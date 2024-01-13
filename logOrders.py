from config import *
import requests
import datetime
import time

ROOM_CAPACITY_MAP = {
	0: 0,
	# SACRO CUORE
	83: 11,
	67: 50,
	68: 45,
	69: 84,
	70: 10,

	# OVERFLOW 1
	75: 50
}

def ans(data, name):
	for p in data['positions']:
		for a in p['answers']:
			if a.get('question_identifier', None) == name:
				if a['answer'] in ['True', 'False']:
					return bool(a['answer'] == 'True')
				return a['answer']
	return None

def getOrders():
	ret = []
	p = 0
		
	while 1:
		p += 1
		res = requests.get(f"{base_url_event}orders/?page={p}", headers=headers)

		if res.status_code == 404: break

		data = res.json()
		for o in data['results']:
			
			roomType = 0

			for pos in o['positions']:
				if pos['item'] == ITEMS_ID_MAP['bed_in_room']:
					roomType = pos['variation']

			ret.append({"code": o['code'], "fname": ans(o, 'fursona_name'), "rType": roomType, "date": o['datetime']})
	return ret

ordersCode = set()
ordersTime = set()
ordersFName = set()
while True:
	#try:
	newOrders = getOrders()
	shouldSleep = True
	for o in newOrders:
		if o['code'] not in ordersCode and not o['date'] in ordersTime and not o['fname'] in ordersFName:

			remainingInRoomType = ROOM_CAPACITY_MAP[o['rType']]
			remainingInRoomType -= 1
			ROOM_CAPACITY_MAP[o['rType']] = remainingInRoomType

			roomCapacitiesStr = ", ".join(str(x).rjust(2, "0") for x in ROOM_CAPACITY_MAP.values())
			#dateStr = datetime.datetime.now().isoformat()

			print(f"[{o['date']}] {len(ordersCode)} - [{o['code']}] New order! FursonaName: {o['fname'].ljust(24)} - Room capacities: {roomCapacitiesStr}")

			shouldSleep = False
			time.sleep(0.05)
		ordersCode.add(o['code'])
		ordersTime.add(o['date'])
		ordersFName.add(o['fname'])
	#except:
	#	print("Exception occurred!")
	#	pass
	if shouldSleep:
		time.sleep(1)
