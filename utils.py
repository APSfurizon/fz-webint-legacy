from os.path import join
from sanic import exceptions
from config import *
import httpx
from messages import ROOM_ERROR_TYPES
from email_util import send_unconfirm_message
from sanic.log import logger

METADATA_TAG = "meta_data"
VARIATIONS_TAG = "variations"

QUESTION_TYPES = { #https://docs.pretix.eu/en/latest/api/resources/questions.html
	"number": "N",
	"one_line_string": "S",
	"multi_line_string": "T",
	"boolean": "B",
	"choice_from_list": "C",
	"multiple_choice_from_list": "M",
	"file_upload": "F",
	"date": "D",
	"time": "H",
	"date_time": "W",
	"country_code": "CC",
	"telephone_number": "TEL"
}
TYPE_OF_QUESTIONS = {} # maps questionId -> type


async def load_questions():
	global TYPE_OF_QUESTIONS
	TYPE_OF_QUESTIONS.clear()
	async with httpx.AsyncClient() as client:
		p = 0
		while 1:
			p += 1
			res = await client.get(join(base_url_event, f"questions/?page={p}"), headers=headers)

			if res.status_code == 404: break

			data = res.json()
			for q in data['results']:
				TYPE_OF_QUESTIONS[q['id']] = q['type']

async def load_items():
	global ITEMS_ID_MAP
	global ITEM_VARIATIONS_MAP
	global CATEGORIES_LIST_MAP
	global ROOM_TYPE_NAMES
	async with httpx.AsyncClient() as client:
		p = 0
		while 1:
			p += 1
			res = await client.get(join(base_url_event, f"items/?page={p}"), headers=headers)

			if res.status_code == 404: break

			data = res.json()
			for q in data['results']:
				# Map item id
				itemName = check_and_get_name ('item', q)
				if itemName and itemName in ITEMS_ID_MAP:
					ITEMS_ID_MAP[itemName] = q['id']
				# If item has variations, map them, too
				if itemName in ITEM_VARIATIONS_MAP and VARIATIONS_TAG in q:
					isBedInRoom = itemName == 'bed_in_room'
					for v in q[VARIATIONS_TAG]:
						variationName = check_and_get_name('variation', v)
						if variationName and variationName in ITEM_VARIATIONS_MAP[itemName]:
							ITEM_VARIATIONS_MAP[itemName][variationName] = v['id']
							if isBedInRoom and variationName in ITEM_VARIATIONS_MAP['bed_in_room']:
								roomName = v['name'] if 'name' in v and isinstance(v['name'], str) else None
								if not roomName and 'value' in v:
									roomName = v['value'][list(v['value'].keys())[0]]
								ROOM_TYPE_NAMES[v['id']] = roomName
				# Adds itself to the category list
				categoryName = check_and_get_category ('item', q)
				if not categoryName: continue
				CATEGORIES_LIST_MAP[categoryName].append(q['id'])
		if (EXTRA_PRINTS):
			logger.debug(f'Mapped Items: %s', ITEMS_ID_MAP)
			logger.debug(f'Mapped Variations: %s', ITEM_VARIATIONS_MAP)
			logger.debug(f'Mapped categories: %s', CATEGORIES_LIST_MAP)
			logger.debug(f'Mapped Rooms: %s', ROOM_TYPE_NAMES)

# Tries to get an item name from metadata. Prints a warning if an item has no metadata
def check_and_get_name(type, q):
	itemName = extract_metadata_name(q)
	if not itemName and EXTRA_PRINTS:			
		logger.warning('%s %s has not been mapped.', type, q['id'])
	return itemName

def check_and_get_category (type, q):
	categoryName = extract_category (q)
	if not categoryName and EXTRA_PRINTS:
		logger.warning('%s %s has no category set.', type, q['id'])
	return categoryName

# Checks if the item has specified metadata name
def internal_name_check (toExtract, name):
	return toExtract and name and METADATA_TAG in toExtract and toExtract[METADATA_TAG][METADATA_NAME] == str(name)

# Returns the item_name metadata from the item or None if not defined
def extract_metadata_name (toExtract):
	return extract_data(toExtract, [METADATA_TAG, METADATA_NAME])

# Returns the category_name metadata from the item or None if not defined
def extract_category (toExtract):
	return extract_data(toExtract, [METADATA_TAG, METADATA_CATEGORY])

def extract_data (dataFrom, tags):
	data = dataFrom
	for t in tags:
		if t not in data: return None
		data = data[t]
	return data

def key_from_value(dict, value):
    return [k for k,v in dict.items() if v == value]

def sizeof_fmt(num, suffix="B"):
    for unit in ("", "K", "M", "G", "T", "P", "E", "Z"):
        if abs(num) < 1000.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1000.0
    return f"{num:.1f}Yi{suffix}"

async def get_order_by_code(request, code, throwException=False):
	res = await request.app.ctx.om.get_order(code=code)
	if not throwException:
		return res
	if res is None:
		raise exceptions.BadRequest(f"[getOrderByCode] Code {code} not found!")
	return res

async def get_people_in_room_by_code(request, code, om=None):
	if not om: om = request.app.ctx.om
	await om.update_cache()
	return filter(lambda rm: rm.room_id == code, om.cache.values())

async def unconfirm_room_by_order(order, room_members:[]=None, throw=True, request=None, om=None):
	if not om: om = request.app.ctx.om
	if not order.room_confirmed:
		if throw:
			raise exceptions.BadRequest("Room is not confirmed!")
		else:
			return
		
	room_members = await get_people_in_room_by_code(request, order.code, om) if not room_members or len(room_members) == 0 else room_members
	for p in room_members:
		await p.edit_answer('room_confirmed', "False")
		await p.send_answers()

async def validate_rooms(request, rooms, om):
	logger.info('Validating rooms...')
	if not om: om = request.app.ctx.om

	# rooms_to_unconfirm is the room that MUST be unconfirmed, room_with_errors is a less strict set containing all rooms with kind-ish errors
	rooms_to_unconfirm = []
	room_with_errors = []

	# Validate rooms
	for order in rooms:
		result = await check_room(request, order, om)
		if(len(order.room_errors) > 0):
			room_with_errors.append(result)
		check = result[1]
		if check != None and check == False:
			rooms_to_unconfirm.append(result)
	
	# End here if no room has failed check
	if len(room_with_errors) == 0: 
		logger.info('[ROOM VALIDATION] Every room passed the check.')
		return

	roomErrListSrts = []
	for fr in room_with_errors:
		for error in fr[0].room_errors:
			roomErrListSrts.append(f"[ROOM VALIDATION] [ERR] Parent room: {fr[0].code} {'C' if fr[0].room_confirmed else 'N'} | Order {error[0] if error[0] else '-----'} with code {error[1]}")
	logger.warning(f'[ROOM VALIDATION] Room validation failed for orders: \n%s', "\n".join(roomErrListSrts))
	
	# Get confirmed rooms that fail validation
	failed_confirmed_rooms = list(filter(lambda fr: (fr[0].room_confirmed == True), rooms_to_unconfirm))

	if len(failed_confirmed_rooms) == 0:
		logger.info('[ROOM VALIDATION] No rooms to unconfirm.')
		return

	logger.info(f"[ROOM VALIDATION] Trying to unconfirm {len(failed_confirmed_rooms)} rooms...")

	# Try unconfirming them
	for rtu in failed_confirmed_rooms:
		order = rtu[0]
		member_orders = rtu[2]
		
		# Unconfirm and email users about the room
		await unconfirm_room_by_order(order, member_orders, False, None, om)

	logger.info(f"[ROOM VALIDATION] Sending unconfirm notice to room members...")
	sent_count = 0
	# Send unconfirm notice via email
	for rtu in failed_confirmed_rooms:
		order = rtu[0]
		member_orders = rtu[2]
		try:
			await send_unconfirm_message (order, member_orders)
			sent_count += len(member_orders)
		except Exception as ex:
			if EXTRA_PRINTS: logger.exception(str(ex))
	logger.info(f"[ROOM VALIDATION] Sent {sent_count} emails")
		

async def check_room(request, order, om=None):
	room_errors = []
	room_members = []
	use_cached = request == None
	if not om: om = request.app.ctx.om
	if not order or not order.room_id or order.room_id != order.code: return (order, False, room_members)
	
	# This is not needed anymore you buy tickets already 
	#if quotas.get_left(len(order.room_members)) == 0:
	#	raise exceptions.BadRequest("There are no more rooms of this size to reserve.")
	allOk = True

	bed_in_room = order.bed_in_room # Variation id of the ticket for that kind of room
	for m in order.room_members:
		if m == order.code:
			res = order
		else:
			res = await om.get_order(code=m, cached=use_cached)
		
		# Room user in another room
		if res.room_id != order.code:
			room_errors.append((res.code, 'room_id_mismatch'))
			allOk = False
		
		if res.status != 'paid':
			room_errors.append((res.code, 'unpaid'))
		
		if res.bed_in_room != bed_in_room:
			room_errors.append((res.code, 'type_mismatch'))
			if order.room_confirmed:
				allOk = False
		
		if res.daily:
			room_errors.append((res.code, 'daily'))
			if order.room_confirmed:
				allOk = False
			
		room_members.append(res)
	
	if len(room_members) != order.room_person_no and order.room_person_no != None:
		room_errors.append((None, 'capacity_mismatch'))
		if order.room_confirmed:
			allOk = False
	order.set_room_errors(room_errors)
	return (order, allOk, room_members)
