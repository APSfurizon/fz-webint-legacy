from dataclasses import dataclass
from sanic import Request, exceptions, Sanic
import httpx
import re
from utils import *
from config import *
from os.path import join
import json
from sanic.log import logger
from time import time
from metrics import *
import asyncio
from threading import Lock
import pretixClient
import traceback

@dataclass
class Order:
	def __init__(self, data):
	
		self.time = time()
		self.data = data
		if(len(self.data['positions']) == 0):
			for fee in data['fees']:
				if(fee['fee_type'] == "cancellation"):
					self.data['status'] = 'c'
		self.status = {'n': 'pending', 'p': 'paid', 'e': 'expired', 'c': 'canceled'}[self.data['status']]
		self.secret = data['secret']

		if not len(self.data['positions']):
			self.status = 'canceled'
		
		self.code = data['code']
		self.pending_update = False
		
		self.email = data['email']
		
		self.has_card = False
		self.sponsorship = None
		self.has_early = False
		self.has_late = False
		self.first_name = "None"
		self.last_name = "None"
		self.country = 'xx'
		self.address = None
		self.checked_in = False
		self.room_type = None
		self.daily = False
		self.dailyDays = []
		self.bed_in_room = -1
		self.room_person_no = -1
		self.answers = []
		self.position_id = -1
		self.position_positionid = -1
		self.position_positiontypeid = -1
		self.barcode = "None"
		
		idata = data['invoice_address']
		if idata:
			self.address = f"{idata['street'].strip()} - {idata['zipcode'].strip()} {idata['city'].strip()} - {idata['country'].strip()}".replace("\n", "").replace("\r", "")
			self.country = idata['country']
		
		for p in self.data['positions']:
			if p['item'] in CATEGORIES_LIST_MAP['tickets']:
				self.position_id = p['id']
				self.position_positionid = p['positionid']
				self.position_positiontypeid = p['item']
				self.answers = p['answers']
				for i, ans in enumerate(self.answers):
					if(TYPE_OF_QUESTIONS[self.answers[i]['question']] == QUESTION_TYPES['file_upload']):
						self.answers[i]['answer'] = "file:keep"
				self.barcode = p['secret']
				self.checked_in = bool(p['checkins'])
			
			if p['item'] in CATEGORIES_LIST_MAP['dailys']:
				self.daily = True
				self.dailyDays.append(CATEGORIES_LIST_MAP['dailys'].index(p['item']))

			if p['item'] in CATEGORIES_LIST_MAP['memberships']:
				self.has_card = True
				
			if p['item'] == ITEMS_ID_MAP['sponsorship_item']:
				sponsorshipType = key_from_value(ITEM_VARIATIONS_MAP['sponsorship_item'], p['variation'])
				self.sponsorship = sponsorshipType[0].replace ('sponsorship_item_', '') if len(sponsorshipType) > 0 else None
				
			if p['attendee_name']:
				self.first_name = p['attendee_name_parts']['given_name']
				self.last_name = p['attendee_name_parts']['family_name']
				
			if p['item'] == ITEMS_ID_MAP['early_arrival_admission']:
				self.has_early = True
			
			if p['item'] == ITEMS_ID_MAP['late_departure_admission']:
				self.has_late = True

			if p['item'] == ITEMS_ID_MAP['bed_in_room']:
				roomTypeLst = key_from_value(ITEM_VARIATIONS_MAP['bed_in_room'], p['variation'])
				roomTypeId = roomTypeLst[0] if len(roomTypeLst) > 0 else None
				self.bed_in_room = p['variation']
				self.room_person_no = ROOM_CAPACITY_MAP[roomTypeId] if roomTypeId in ROOM_CAPACITY_MAP else self.room_person_no
		
		self.total = float(data['total'])
		self.fees = 0
		self.refunds = 0
		for fee in data['fees']:
			self.fees += float(fee['value'])
			
		for ref in data['refunds']:
			self.refunds += float(ref['amount'])
		
		answers = ['payment_provider', 'shirt_size', 'birth_date', 'fursona_name', 'room_confirmed', 'room_id']
		
		self.payment_provider = data['payment_provider']
		self.comment = data['comment']
		self.phone = data['phone']
		self.room_errors = []
		self.loadAns()
		
		if(self.bed_in_room < 0 and not self.daily):
			self.status = "canceled" # Must refer to the previous status assignment
	def loadAns(self):
		self.shirt_size = self.ans('shirt_size')
		self.is_artist = True if self.ans('is_artist') != 'No' else False
		self.is_fursuiter = True if self.ans('is_fursuiter') != 'No' else False
		self.is_allergic = True if self.ans('is_allergic') != 'No' else False
		self.notes = self.ans('notes')
		self.badge_id = int(self.ans('badge_id')) if self.ans('badge_id') else None
		self.propic_locked = self.ans('propic_locked')
		self.propic_fursuiter = self.ans('propic_fursuiter')
		self.propic = self.ans('propic')
		self.carpooling_message = json.loads(self.ans('carpooling_message')) if self.ans('carpooling_message') else {}
		self.karaoke_songs = json.loads(self.ans('karaoke_songs')) if self.ans('karaoke_songs') else {}
		self.birth_date = self.ans('birth_date')
		self.birth_location = self.ans('birth_location')
		self.name = self.ans('fursona_name')
		self.room_id = self.ans('room_id')
		self.room_confirmed = self.ans('room_confirmed')
		self.room_name = self.ans('room_name')
		self.pending_room = self.ans('pending_room')
		self.pending_roommates = self.ans('pending_roommates').split(',') if self.ans('pending_roommates') else []
		self.room_members = self.ans('room_members').split(',') if self.ans('room_members') else []
		self.room_owner = (self.code is not None and self.room_id is not None and self.code.strip() == self.room_id.strip())
		self.room_secret = self.ans('room_secret')
		self.app_token = self.ans('app_token')
		self.nfc_id = self.ans('nfc_id')
		self.can_scan_nfc = True if self.ans('can_scan_nfc') != 'No' else False
		self.actual_room = self.ans('actual_room')
		self.staff_role = self.ans('staff_role')
		self.telegram_username = self.ans('telegram_username').strip('@') if self.ans('telegram_username') else None
		self.shuttle_bus = self.ans('shuttle_bus')
	def __getitem__(self, var):
		return self.data[var]
	
	def set_room_errors (self, to_set):
			self.room_errors = to_set

	def ans(self, name):
		for p in self.data['positions']:
			for a in p['answers']:
				if a.get('question_identifier', None) == name:
					if a['answer'] in ['True', 'False']:
						return bool(a['answer'] == 'True')
					return a['answer']
		return None
	
	def isBadgeValid (self):
		return self.ans('propic') and (not self.is_fursuiter or self.ans('propic_fursuiter'))
	
	def isAdmin (self):
		return self.code in ADMINS or self.staff_role in ADMINS_PRETIX_ROLE_NAMES
		
	async def edit_answer_fileUpload(self, name, fileName, mimeType, data : bytes):
		if(mimeType != None and data != None):
			localHeaders = dict(headers)
			localHeaders['Content-Type'] = mimeType
			localHeaders['Content-Disposition'] = f'attachment; filename="{fileName}"'
			res = await pretixClient.post("upload", baseUrl=base_url, headers=localHeaders, content=data, expectedStatusCodes=[201])
			res = res.json()
			await self.edit_answer(name, res['id'])
		else:
			await self.edit_answer(name, None)
		self.loadAns()

	async def edit_answer(self, name, new_answer):
		found = False
		self.pending_update = True
		for key in range(len(self.answers)):
			if self.answers[key].get('question_identifier', None) == name:
				if new_answer != None:
					if DEV_MODE and EXTRA_PRINTS: logger.debug('[ANSWER EDIT] EXISTING ANSWER UPDATE %s => %s', name, new_answer)
					self.answers[key]['answer'] = new_answer
					found = True
				else:
					if DEV_MODE and EXTRA_PRINTS: logger.debug('[ANSWER EDIT] DEL ANSWER %s => %s', name, new_answer)
					del self.answers[key]

				break
					
		if (not found) and (new_answer is not None):
			res = await pretixClient.get("questions/")
			res = res.json()
			for r in res['results']:
				if r['identifier'] != name: continue
			
				if DEV_MODE and EXTRA_PRINTS: logger.debug(f'[ANSWER EDIT] %s => %s', name, new_answer)
				self.answers.append({
					'question': r['id'],
					'answer': new_answer,
					'options': r['options']
				})
		self.loadAns()
			
	async def send_answers(self):
		if DEV_MODE and EXTRA_PRINTS: logger.debug("[ANSWER POST] POSITION ID IS %s", self.position_id)
		
		for i, ans in enumerate(self.answers):
			if TYPE_OF_QUESTIONS[ans['question']] == QUESTION_TYPES["multiple_choice_from_list"]: # if multiple choice
				identifier = ans['question_identifier']
				if self.ans(identifier) == "": #if empty answer 
					await self.edit_answer(identifier, None)
			# Fix for karaoke fields
			#if ans['question'] == 40:
			#	del self.answers[i]['options']
			#	del self.answers[i]['option_identifiers']

		ans = [] if self.status == "canceled" else self.answers 
		res = await pretixClient.patch(f'orderpositions/{self.position_id}/', json={'answers': ans}, expectedStatusCodes=None)
		
		if res.status_code != 200:
			e = res.json()
			if "answers" in e:
				for ans, err in zip(self.answers, res.json()['answers']):
					if err:
						logger.error ('[ANSWERS SENDING] ERROR ON %s %s', ans, err)
			else:
				logger.error("[ANSWERS SENDING] GENERIC ERROR. Response: '%s'", str(e))

			raise exceptions.ServerError('There has been an error while updating this answers.')
		
		for i, ans in enumerate(self.answers):
			if(TYPE_OF_QUESTIONS[self.answers[i]['question']] == QUESTION_TYPES['file_upload']):
				self.answers[i]['answer'] = "file:keep"
			
		self.pending_update = False
		self.time = -1
		self.loadAns()
		
	def get_language(self):
		return self.country.lower() if self.country.lower() in AVAILABLE_LOCALES else 'en'
	
	def __str__(self):
		to_return = f"{'Room' if self.room_owner else 'Order'} {self.code}"
		if self.room_owner == True:
			to_return = f"{to_return} [ members = {self.room_members} ]"
		return to_return
	
	def __repr__(self):
		to_return = f"{'Room' if self.room_owner == True else 'Order'} {self.code}"
		if self.room_owner == True:
			to_return = f"{to_return} [ members = {self.room_members} ]"
		return to_return

@dataclass
class Quota:
	def __init__(self, data):
		self.items = data['items'] if 'items' in data else []
		self.variations = data['variations'] if 'variations' in data else []
		self.available = data['available'] if 'available' in data else False
		self.size = data['size'] if 'size' in data else 0
		self.available_number = data['available_number'] if 'available_number' in data else 0

	def has_item (self, id: int=-1, variation: int=None):
		return id in self.items if not variation else (id in self.items and variation in self.variations)

	def get_left (self):
		return self.available_number
	
	def __repr__(self):
		return f'Quota [items={self.items}, variations={self.variations}] [{self.available_number}/{self.size}]'

	def __str__(self):
		return f'Quota [items={self.items}, variations={self.variations}] [{self.available_number}/{self.size}]'

def get_quota(item: int, variation: int = None) -> Quota:
	ret : Quota = None
	for q in QUOTA_LIST:
		if (q.has_item(item, variation)):
			if(ret == None or (q.size != None and q.size < ret.size)):
				ret = q
	return ret

@dataclass
class Quotas:
	def __init__(self, data):
		self.data = data
		
	def get_left(self, capacity):
		for quota in self.data['results']:
			if quota['id'] == ROOM_QUOTA_ID[capacity]:
				return quota['available_number']
		return 0	

async def get_quotas(request: Request=None):
	res = await pretixClient.get('quotas/?order=id&with_availability=true')
	res = res.json()
	
	return Quotas(res)

async def load_item_quotas() -> bool:
	global QUOTA_LIST
	QUOTA_LIST = []
	logger.info ('[QUOTAS] Loading quotas...')
	success = True
	try:
		res = await pretixClient.get('quotas/?order=id&with_availability=true')
		res = res.json()
		for quota_data in res['results']:
			QUOTA_LIST.append (Quota(quota_data))
	except Exception:
		logger.warning(f"[QUOTAS] Error while loading quotas.\n{traceback.format_exc()}")
		success = False
	return success

async def get_order(request: Request=None):
	await request.receive_body()
	return await request.app.ctx.om.get_order(request=request)

class OrderManager:
	def __init__(self):
		self.lastCacheUpdate = 0
		self.updating : Lock = Lock()
		self.empty()

	def empty(self):
		self.cache = {}
		self.order_list = []

	# Will fill cache once the last cache update is greater than cache expire time
	async def update_cache(self, check_itemsQuestions=False):
		t = time()
		to_return = False
		success = True
		if(t - self.lastCacheUpdate > CACHE_EXPIRE_TIME and not self.updating.locked()):
			to_return = True
			success = await self.fill_cache(check_itemsQuestions=check_itemsQuestions)
		return (to_return, success)

	def add_cache(self, order, cache=None, orderList=None):
		# Extra params for dry runs
		if(cache is None):
			cache = self.cache
		if(orderList is None):
			orderList = self.order_list

		cache[order.code] = order
		if not order.code in orderList:
			orderList.append(order.code)

	def remove_cache(self, code, cache=None, orderList=None):
		# Extra params for dry runs
		if(cache is None):
			cache = self.cache
		if(orderList is None):
			orderList = self.order_list

		if code in cache:
			del cache[code]
			orderList.remove(code)
	

	async def fill_cache(self, check_itemsQuestions=False) -> bool:
		# Check cache lock
		logger.info(f"[CACHE] Lock status: {self.updating.locked()}")
		self.updating.acquire()
		ret = False
		exp = None
		try:
			ret = await self.fill_cache_INTERNAL(check_itemsQuestions=check_itemsQuestions)
		except Exception as e: 
			exp = e
		self.updating.release()
		logger.info(f"[CACHE] Ret status: {ret}. Exp: {exp}")
		if(exp != None):
			raise exp
		return ret

	async def fill_cache_INTERNAL(self, check_itemsQuestions=False) -> bool:
		start_time = time()
		logger.info("[CACHE] Filling cache...")
		# Index item's ids
		r = await load_items()
		if(not r and check_itemsQuestions):
			logger.error("[CACHE] Items were not loading correctly. Aborting filling cache...")
			return False

		# Index questions' types
		r = await load_questions()
		if(not r and check_itemsQuestions):
			logger.error("[CACHE] Questions were not loading correctly. Aborting filling cache...")
			return False

		# Load quotas
		r = await load_item_quotas()
		if(not r and check_itemsQuestions):
			logger.error("[CACHE] Quotas were not loading correctly. Aborting filling cache...")
			return False

		cache = {}
		orderList = []
		success = True
		p = 0
		try:
			while 1:
				p += 1
				res = await pretixClient.get(f"orders/?page={p}", expectedStatusCodes=[200, 404])
				if res.status_code == 404: break
				# Parse order data
				data = res.json()
				for o in data['results']:
					o = Order(o)
					if o.status in ['canceled', 'expired']:
						self.remove_cache(o.code, cache=cache, orderList=orderList)
					else:
						self.add_cache(Order(o), cache=cache, orderList=orderList)
			self.lastCacheUpdate = time()
			logger.info(f"[CACHE] Cache filled in {self.lastCacheUpdate - start_time}s.")
		except Exception:
			logger.error(f"[CACHE] Error while refreshing cache.\n{traceback.format_exc()}")
			success = False

		# Apply new cache if there were no errors
		if(success):
			self.cache = cache
			self.order_list = orderList

		# Validating rooms
		rooms = list(filter(lambda o: (o.code == o.room_id), self.cache.values()))
		asyncio.create_task(validate_rooms(None, rooms, self))

		return success

	async def get_order(self, request=None, code=None, secret=None, nfc_id=None, cached=False):

		# if it's a nfc id, just retorn it
		if nfc_id:
			for order in self.cache.values():
				if order.nfc_id == nfc_id:
					return order
	
		await self.update_cache()
		# If a cached order is needed, just get it if available
		if code and cached and code in self.cache and time()-self.cache[code].time < 3600:
			return self.cache[code]
	
		# If it's a request, ignore all the other parameters and just get the order of the requestor
		if request:
			code = request.cookies.get("foxo_code")
			secret = request.cookies.get("foxo_secret")
		
		if re.match('^[A-Z0-9]{5}$', code or '') and (secret is None or re.match('^[a-z0-9]{16,}$', secret)):
			if DEV_MODE and EXTRA_PRINTS: logger.debug(f'Fetching {code} with secret {secret}')

			res = await pretixClient.get(f"orders/{code}/", expectedStatusCodes=None)
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