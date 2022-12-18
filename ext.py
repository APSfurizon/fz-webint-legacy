from dataclasses import dataclass
from sanic import Request, exceptions
import httpx
import re
from config import *
from os.path import join

@dataclass
class Order:
	def __init__(self, data):
		self.data = data
		self.status = {'n': 'pending', 'p': 'paid', 'e': 'expired', 'c': 'canceled'}[self.data['status']]
		self.code = data['code']
		
		for p in self.data['positions']:
			if p['item'] not in [16, 38]:
				continue		

			self.position_id = p['id']
			self.position_positionid = p['positionid']
			self.answers = p['answers']

		self.name = self.ans('fursona_name')
		self.room_id = self.ans('room_id')
		self.room_confirmed = self.ans('room_confirmed')
		self.pending_room = self.ans('pending_room')
		self.pending_roommates = self.ans('pending_roommates').split(',') if self.ans('pending_roommates') else []
		self.room_members = self.ans('room_members').split(',') if self.ans('room_members') else []
		self.room_owner = (self.code == self.room_id)
		self.room_secret = self.ans('room_secret')

	def __getitem__(self, var):
		return self.data[var]

	def ans(self, name):
		for a in self.answers:
			if a['question_identifier'] == name:
				if a['answer'] in ['True', 'False']:
					return bool(a['answer'] == 'True')
				return a['answer']
		return None
		
	async def edit_answer(self, name, new_answer):
		found = False
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

async def get_order(request: Request=None, code=None, secret=None, insecure=False):
	if request:
		await request.receive_body()
		code = request.cookies.get("foxo_code")
		secret = request.cookies.get("foxo_secret")
	
	if re.match('^[A-Z0-9]{5}$', code or '') and (secret is None or re.match('^[a-z0-9]{16,}$', secret)):
		print('Trying to get a session from stored', code, secret)
		async with httpx.AsyncClient() as client:
			res = await client.get(join(base_url, f"orders/{code}/"), headers=headers)
			if res.status_code != 200:
				if request:
					raise exceptions.Forbidden("Your session has expired due to order deletion or change! Please check your E-Mail for more info.")
			
			res = res.json()
		
			if res['status'] in ['c', 'e']:
				if request:
					raise exceptions.Forbidden(f"Your order has been deleted. Contact support with your order identifier ({res['code']}) for further info.")
		
			if secret == res['secret'] or insecure:
				return Order(res)
			else:
				if request:
					raise exceptions.Forbidden("Your session has expired due to a token change. Please check your E-Mail for an updated link!")
	return None
