from os.path import join
from sanic import exceptions
from config import *
import httpx

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
			print (f'Mapped Items:')
			print (ITEMS_ID_MAP)
			print (f'Mapped Variations:')
			print (ITEM_VARIATIONS_MAP)
			print (f'Mapped categories:')
			print (CATEGORIES_LIST_MAP)
			print (f'Mapped Rooms:')
			print (ROOM_TYPE_NAMES)

# Tries to get an item name from metadata. Prints a warning if an item has no metadata
def check_and_get_name(type, q):
	itemName = extract_metadata_name(q)
	if not itemName and EXTRA_PRINTS:			
		print (type + ' ' + q['id'] + ' has not been mapped.')
	return itemName

def check_and_get_category (type, q):
	categoryName = extract_category (q)
	if not categoryName and EXTRA_PRINTS:
		print (type + ' ' + q['id'] + ' has no category set.')
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

def get_people_in_room_by_code(request, code):
	c = request.app.ctx.om.cache
	ret = []
	for person in c.values():
		if person.room_id == code:
			ret.append(person)
	return ret