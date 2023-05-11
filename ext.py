from dataclasses import dataclass
from sanic import Request, exceptions
import httpx
import re
from config import *
from os.path import join
import json
from time import time

@dataclass
class Order:
	def __init__(self, data):
	
		self.time = time()
		self.data = data
		self.status = {'n': 'pending', 'p': 'paid', 'e': 'expired', 'c': 'canceled'}[self.data['status']]
		
		if not len(self.data['positions']):
			self.status = 'canceled'
		
		self.code = data['code']
		self.pending_update = False
		
		self.email = data['email']
		
		self.has_card = False
		self.sponsorship = None
		self.has_early = False
		self.has_late = False
		self.first_name = None
		self.last_name = None
		self.country = None
		
		for p in self.data['positions']:
			if p['item'] in [16, 38]:
				self.position_id = p['id']
				self.position_positionid = p['positionid']
				self.answers = p['answers']
				self.barcode = p['secret']

			if p['item'] == 17:
				self.has_card = True
				
			if p['item'] == 19:
				self.sponsorship = 'normal' if p['variation'] == 13 else 'super'
				
			if p['country']:
				self.country = p['country']
				
			if p['attendee_name']:
				self.first_name = p['attendee_name_parts']['given_name']
				self.last_name = p['attendee_name_parts']['family_name']
				
			if p['item'] == 20:
				self.has_early = True
			
			if p['item'] == 21:
				self.has_late = True
		
		self.total = float(data['total'])
		self.fees = 0
		self.refunds = 0
		for fee in data['fees']:
			self.fees += float(fee['value'])
			
		for ref in data['refunds']:
			self.refunds += float(ref['amount'])
		
		answers = ['payment_provider', 'shirt_size', 'birth_date', 'fursona_name', 'room_confirmed', 'room_id']
		
		self.payment_provider = data['payment_provider']
		self.shirt_size = self.ans('shirt_size')
		self.is_artist = True if self.ans('is_artist') != 'No' else False
		self.is_fursuiter = True if self.ans('is_fursuiter') != 'No' else False
		self.is_allergic = True if self.ans('is_allergic') != 'No' else False
		self.propic_locked = self.ans('propic_locked')
		self.carpooling_message = json.loads(self.ans('carpooling_message')) if self.ans('carpooling_message') else {}
		self.birth_date = self.ans('birth_date')
		self.name = self.ans('fursona_name')
		self.room_id = self.ans('room_id')
		self.room_confirmed = self.ans('room_confirmed')
		self.room_name = self.ans('room_name')
		self.pending_room = self.ans('pending_room')
		self.pending_roommates = self.ans('pending_roommates').split(',') if self.ans('pending_roommates') else []
		self.room_members = self.ans('room_members').split(',') if self.ans('room_members') else []
		self.room_owner = (self.code == self.room_id)
		self.room_secret = self.ans('room_secret')
		self.app_token = self.ans('app_token')


	def __getitem__(self, var):
		return self.data[var]

	def ans(self, name):
		for p in self.data['positions']:
			for a in p['answers']:
				if a['question_identifier'] == name:
					if a['answer'] in ['True', 'False']:
						return bool(a['answer'] == 'True')
					return a['answer']
		return None
		
	async def edit_answer(self, name, new_answer):
		found = False
		self.pending_update = True
		for key in range(len(self.answers)):
			if self.answers[key]['question_identifier'] == name:
				if new_answer != None:
					print('EXISTING ANSWER UPDATE', name, '=>', new_answer)
					self.answers[key]['answer'] = new_answer
					found = True
				else:
					print('DEL ANSWER', name, '=>', new_answer)
					del self.answers[key]

				break
					
		if (not found) and (new_answer is not None):
			
			async with httpx.AsyncClient() as client:
				res = await client.get(join(base_url, 'questions/'), headers=headers)
				res = res.json()

			for r in res['results']:
				if r['identifier'] != name: continue
			
				print('ANSWER UPDATE', name, '=>', new_answer)
				self.answers.append({
					'question': r['id'],
					'answer': new_answer,
					'question_identifier': r['identifier'],
					'options': r['options']
				})
			
	async def send_answers(self):
		async with httpx.AsyncClient() as client:
			res = await client.patch(join(base_url, f'orderpositions/{self.position_id}/'), headers=headers, json={'answers': self.answers})
		self.pending_update = False
		self.time = -1

@dataclass
class Quotas:
	def __init__(self, data):
		self.data = data
		self.capacity_mapping = {
			1: 16,
			2: 17,
			3: 18,
			4: 19,
			5: 20
		}
		
	def get_left(self, capacity):
		for quota in self.data['results']:
			if quota['id'] == self.capacity_mapping[capacity]:
				return quota['available_number']		

async def get_quotas(request: Request=None):
	async with httpx.AsyncClient() as client:
		res = await client.get(join(base_url, 'quotas/?order=id&with_availability=true'), headers=headers)
		res = res.json()
		
		return Quotas(res)

async def get_order(request: Request=None):
	await request.receive_body()
	return await request.app.ctx.om.get_order(request=request)

class OrderManager:
	def __init__(self):
		self.cache = {}
		self.order_list = []

	def add_cache(self, order):
		self.cache[order.code] = order
		if not order.code in self.order_list:
			self.order_list.append(order.code)

	def remove_cache(self, code):
		if code in self.cache:
			del self.cache[code]
			self.order_list.remove(code)
	
	async def get_order(self, request=None, code=None, secret=None, cached=False):
	
		# Fill the cache on first load
		if not self.cache and FILL_CACHE:
			p = 0
			
			async with httpx.AsyncClient() as client:
				while 1:
					p += 1
					res = await client.get(join(base_url, f"orders/?page={p}"), headers=headers)
		
					if res.status_code == 404: break
		
					data = res.json()
					for o in data['results']:
						o = Order(o)
						if o.status in ['canceled', 'expired']:
							self.remove_cache(o.code)
						else:
							self.add_cache(Order(o))

		# If a cached order is needed, just get it if available
		if code and cached and code in self.cache and time()-self.cache[code].time < 3600:
			return self.cache[code]
	
		# If it's a request, ignore all the other parameters and just get the order of the requestor
		if request:
			code = request.cookies.get("foxo_code")
			secret = request.cookies.get("foxo_secret")
		
		if re.match('^[A-Z0-9]{5}$', code or '') and (secret is None or re.match('^[a-z0-9]{16,}$', secret)):
			print('Fetching', code, 'with secret', secret)

			async with httpx.AsyncClient() as client:
				res = await client.get(join(base_url, f"orders/{code}/"), headers=headers)
				if res.status_code != 200:
					if request:
						raise exceptions.Forbidden("Your session has expired due to order deletion or change! Please check your E-Mail for more info.")
					else:
						self.remove_cache(code)
						return None

				res = res.json()
			
				order = Order(res)
				if order.status in ['canceled', 'expired']:
					self.remove_cache(order.code)
					if request:
						raise exceptions.Forbidden(f"Your order has been deleted. Contact support with your order identifier ({res['code']}) for further info.")
				else:
					self.add_cache(order)
			
				if request and secret != res['secret']:
					raise exceptions.Forbidden("Your session has expired due to a token change. Please check your E-Mail for an updated link!")
				return order
