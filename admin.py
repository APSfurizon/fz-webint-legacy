from sanic import response, redirect, Blueprint, exceptions
from email_util import send_missing_propic_message
from room import unconfirm_room_by_order
from config import *
from utils import *
from ext import *
from io import StringIO
from sanic.log import logger
import csv
import time
import json
import math

bp = Blueprint("admin", url_prefix="/manage/admin")

@bp.middleware
async def credentials_check(request: Request):
	order = await get_order(request)
	if not order:
		raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")
	if EXTRA_PRINTS:
		logger.info(f"Checking admin credentials of {order.code} with secret {order.secret}")
	if not order.isAdmin() : raise exceptions.Forbidden("Birichino :)")



@bp.get('/cache/clear')
async def clear_cache(request, order:Order):
	success = await request.app.ctx.om.fill_cache()
	if not success: raise exceptions.ServerError("An error occurred while loading the cache")
	return redirect(f'/manage/admin')

@bp.get('/loginas/<code>')
async def login_as(request, code, order:Order):
	dOrder = await get_order_by_code(request, code, throwException=True)
	if(dOrder.isAdmin()):
		raise exceptions.Forbidden("You can't login as another admin!")

	if EXTRA_PRINTS:
		logger.info(f"Swapping login: {order.secret} {order.code} -> {dOrder.secret} {code}")
	r = redirect(f'/manage/welcome')
	r.cookies['foxo_code_ORG'] = order.code
	r.cookies['foxo_secret_ORG'] = order.secret
	r.cookies['foxo_code'] = code
	r.cookies['foxo_secret'] = dOrder.secret
	return r

@bp.get('/room/verify')
async def verify_rooms(request, order:Order):
	await clear_cache(request, order)
	already_checked, success = await request.app.ctx.om.update_cache()
	if not already_checked and success:
		orders = filter(lambda x: x.status not in ['c', 'e'] and x.room_id == x.code, request.app.ctx.om.cache.values())
		await validate_rooms(request, orders, None)
	return redirect(f'/manage/admin')

@bp.get('/room/unconfirm/<code>')
async def unconfirm_room(request, code, order:Order):
	dOrder = await get_order_by_code(request, code, throwException=True)
	await unconfirm_room_by_order(order=dOrder, throw=True, request=request)
	return redirect(f'/manage/nosecount')

@bp.get('/room/autoconfirm')
async def autoconfirm_room(request, code, order:Order):
	await clear_cache(request, order)
	orders = request.app.ctx.om.cache.values()
	for order in orders:
		if(order.code == order.room_id and not order.room_confirmed and len(order.room_members) == order.room_person_no):
			logger.info(f"Auto-Confirming room {order.room_id}")
			await confirm_room_by_order(order, request)
	return redirect(f'/manage/admin')

@bp.get('/room/delete/<code>')
async def delete_room(request, code, order:Order):
	await clear_cache(request, order)
	dOrder = await get_order_by_code(request, code, throwException=True)

	ppl = await get_people_in_room_by_code(request, code)
	for p in ppl:
		await p.edit_answer('room_id', None)
		await p.edit_answer('room_confirmed', "False")
		await p.edit_answer('room_name', None)
		await p.edit_answer('pending_room', None)
		await p.edit_answer('pending_roommates', None)
		await p.edit_answer('room_members', None)
		await p.edit_answer('room_owner', None)
		await p.edit_answer('room_secret', None)
		await p.send_answers()
	
	await dOrder.send_answers()
	return redirect(f'/manage/nosecount')

@bp.post('/room/rename/<code>')
async def rename_room(request, code, order:Order):
	await clear_cache(request, order)
	dOrder = await get_order_by_code(request, code, throwException=True)

	name = request.form.get('name')
	if len(name) > 64 or len(name) < 4:
		raise exceptions.BadRequest("Your room name is invalid. Please try another one.")

	await dOrder.edit_answer("room_name", name)
	await dOrder.send_answers()
	return redirect(f'/manage/nosecount')

@bp.get('/room/wizard')
async def room_wizard(request, order:Order):
	'''Tries to autofill unconfirmed rooms and other matches together'''
	# Clear cache first
	await clear_cache(request, order)

	#Separate orders which have incomplete rooms and which have no rooms
	all_orders = {key:value for key,value in sorted(request.app.ctx.om.cache.items(), key=lambda x: len(x[1].room_members), reverse=True) if value.status not in ['c', 'e'] and not value.daily}
	orders = {key:value for key,value in sorted(all_orders.items(), key=lambda x: x[1].ans('fursona_name')) if not value.room_confirmed}
	# Orders with incomplete rooms
	incomplete_orders = {key:value for key,value in orders.items() if value.code == value.room_id and (value.room_person_no - len(value.room_members)) > 0}
	# Roomless furs
	roomless_orders = {key:value for key,value in orders.items() if not value.room_id and not value.daily}

	# Result map
	result_map = {
		'A':{
			'type': 'add_existing',
			'to_add': ['b', 'c']
		},
		'B':{
			'type': 'new',
			'room_type': 5,
			'room_name': 'generated 1',
			'to_add': ['B', 'a', 'c']
		}
	}

	result_map = {}

	# Get room quotas
	room_quota_map = {}
	for key, value in ITEM_VARIATIONS_MAP['bed_in_room'].items():
		capacity = ROOM_CAPACITY_MAP[key] if key in ROOM_CAPACITY_MAP else 1
		room_quota_map[value] = math.ceil((len(list(filter(lambda y: y.bed_in_room == value, orders.values())))) / capacity)

	print('RMQ = ')
	print(room_quota_map)

	# Fill already existing rooms
	for room_order in incomplete_orders.items():
		room = room_order[1]
		to_add = []
		missing_slots = room.room_person_no - len(room.room_members)
		for i in range(missing_slots):
			compatible_roomates = {key:value for key,value in roomless_orders.items() if value.bed_in_room == room.bed_in_room}
			if len(compatible_roomates.items()) == 0: break
			# Try picking a roomate that's from the same country and room type
			country = room.country.lower()
			roomless_by_country = {key:value for key,value in compatible_roomates.items() if value.country.lower() == country}
			if len(roomless_by_country.items()) > 0:
				code_to_add = list(roomless_by_country.keys())[0]
				to_add.append(code_to_add)
				del roomless_orders[code_to_add]
			else:
				# If not, add first roomless there is
				code_to_add = list(compatible_roomates.keys())[0]
				to_add.append(code_to_add)
				del roomless_orders[code_to_add]
		result_map[room.code] = {
			'type': 'add_existing',
			'to_add': to_add
		}
	
	generated_counter = 0
	# Create additional rooms
	while len(roomless_orders.items()) > 0:
		room = list(roomless_orders.items())[0][1]
		to_add = []
		missing_slots = room.room_person_no - len(room.room_members)
		for i in range(missing_slots):
			compatible_roomates = {key:value for key,value in roomless_orders.items() if value.bed_in_room == room.bed_in_room}
			if len(compatible_roomates.items()) == 0: break
			# Try picking a roomate that's from the same country and room type
			country = room.country.lower()
			roomless_by_country = {key:value for key,value in compatible_roomates.items() if value.country.lower() == country}
			if len(roomless_by_country.items()) > 0:
				code_to_add = list(roomless_by_country.keys())[0]
				to_add.append(code_to_add)
				del roomless_orders[code_to_add]
			else:
				# If not, add first roomless there is
				code_to_add = list(compatible_roomates.keys())[0]
				to_add.append(code_to_add)
				del roomless_orders[code_to_add]
		generated_counter += 1
		result_map[room.code] = {
			'type': 'new',
			'room_name': f'Generated Room {generated_counter}',
			'room_type': room.bed_in_room,
			'to_add': to_add
		}
	
	result_map["infinite"] = { 'to_add': [] }
	tpl = request.app.ctx.tpl.get_template('wizard.html')
	return html(tpl.render(order=order, all_orders=all_orders, unconfirmed_orders=orders, data=result_map, jsondata=json.dumps(result_map, skipkeys=True, ensure_ascii=False)))

@bp.get('/propic/remind')
async def propic_remind_missing(request, order:Order):
	await clear_cache(request, order)

	orders = request.app.ctx.om.cache.values()
	order: Order
	for order in orders:
		missingPropic = order.propic is None
		missingFursuitPropic = order.is_fursuiter and order.propic_fursuiter is None
		if(missingPropic or missingFursuitPropic):
			# print(f"{order.code}: prp={missingPropic} fpr={missingFursuitPropic} - {order.name}")
			await send_missing_propic_message(order, missingPropic, missingFursuitPropic)

	return redirect(f'/manage/admin')

@bp.get('/export/export')
async def export_export(request, order:Order):
	await clear_cache(request, order)

	data = StringIO()
	w = csv.writer(data)

	w.writerow(['Status', 'Code', 'First name', 'Last name', 'Nick', 'State', 'Card', 'Artist', 'Fursuiter', 'Sponsorhip', 'Early', 'Late', 'Daily', 'Daily days', 'Shirt', 'Room type', 'Room count', 'Room members', 'Payment', 'Price', 'Refunds', 'Staff'])

	orders = request.app.ctx.om.cache.values()
	order: Order
	for order in orders:
		w.writerow([
			order.status,
			order.code,
			order.first_name,
			order.last_name,
			order.name,
			order.country,
			order.has_card,
			order.is_artist,
			order.is_fursuiter,
			order.sponsorship,
			order.has_early,
			order.has_late,
			order.daily,
			','.join(order.dailyDays),
			order.shirt_size,
			ROOM_TYPE_NAMES[order.bed_in_room] if order.bed_in_room in ROOM_TYPE_NAMES else "-",
			len(order.room_members),
			','.join(order.room_members),
			order.payment_provider,
			order.total - order.fees,
			order.refunds,
			order.ans('staff_role') or 'attendee',
		])

	data.seek(0)
	str = data.read() #data.read().decode("UTF-8")
	data.flush()
	data.close()

	return raw(str, status=200, headers={'Content-Disposition': f'attachment; filename="export_{int(time.time())}.csv"', "Content-Type": "text/csv; charset=UTF-8"})

@bp.get('/export/hotel')
async def export_hotel(request, order:Order):
	await clear_cache(request, order)

	data = StringIO()
	w = csv.writer(data)

	w.writerow(['Room type', 'Room name', 'Room code', 'First name', 'Last name', 'Birthday', 'Address', 'Email', 'Phone number', 'Status'])

	orders = sorted(request.app.ctx.om.cache.values(), key=lambda d: (d.room_id if d.room_id != None else "~"))
	order: Order
	for order in orders:
		w.writerow([
			ROOM_TYPE_NAMES[order.bed_in_room] if order.bed_in_room in ROOM_TYPE_NAMES else "-",
			order.room_name,
			order.room_id,
			order.first_name,
			order.last_name,
			order.birth_date,
			order.address,
			order.email,
			order.phone,
			order.status,
			order.code
		])

	data.seek(0)
	str = data.read() #data.read().decode("UTF-8")
	data.flush()
	data.close()

	return raw(str, status=200, headers={'Content-Disposition': f'attachment; filename="hotel_{int(time.time())}.csv"', "Content-Type": "text/csv; charset=UTF-8"})