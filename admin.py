from sanic import response, redirect, Blueprint, exceptions
from email_util import send_missing_propic_message
from random import choice
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
	all_orders = {key:value for key,value in sorted(request.app.ctx.om.cache.items(), key=lambda x: (x[1].room_person_no, len(x[1].room_members)), reverse=True) if (value.status not in ['canceled', 'expired'] and not value.daily and value.bed_in_room != ITEM_VARIATIONS_MAP["bed_in_room"]["bed_in_room_no_room"])}
	orders = {key:value for key,value in sorted(all_orders.items(), key=lambda x: x[1].ans('fursona_name')) if not value.room_confirmed}
	# Orders with incomplete rooms
	incomplete_orders = {key:value for key,value in orders.items() if value.code == value.room_id and (value.room_person_no - len(value.room_members)) > 0}
	# Roomless furs
	roomless_orders = {key:value for key,value in orders.items() if(not value.room_id and not value.daily and value.bed_in_room != ITEM_VARIATIONS_MAP["bed_in_room"]["bed_in_room_no_room"])}

	# Result map
	result_map = {}

	# Check overflows
	room_quota_overflow = {}
	for key, value in ITEM_VARIATIONS_MAP['bed_in_room'].items():
		if key != "bed_in_room_no_room":
			room_quota = get_quota(ITEMS_ID_MAP['bed_in_room'], value)
			capacity = ROOM_CAPACITY_MAP[key] if key in ROOM_CAPACITY_MAP else 1
			current_quota = len(list(filter(lambda y: y.bed_in_room == value and y.room_owner == True, all_orders.values())))
			room_quota_overflow[value] = current_quota - int(room_quota.size / capacity) if room_quota else 0
			if DEV_MODE and EXTRA_PRINTS:
				print(f"There are {current_quota} of room type {key} out of a total of ({room_quota.size} / {capacity})")

	# Init rooms to remove
	result_map["void"] = []

	# Remove rooms that are over quota
	for room_type, overflow_qty in {key:value for key,value in room_quota_overflow.items() if value > 0}.items():
		sorted_rooms = sorted(incomplete_orders.values(), key=lambda r: len(r.room_members))
		sorted_rooms = [r for r in sorted_rooms if r.bed_in_room == room_type]
		for room_to_remove in sorted_rooms[:overflow_qty]:
			# Room codes to remove
			result_map["void"].append(room_to_remove.code)
			# Move room members to the roomless list
			for member_code in room_to_remove.room_members:
				roomless_orders[member_code] = all_orders[member_code]
			del incomplete_orders[room_to_remove.code]

	# Fill already existing rooms
	for room_order in incomplete_orders.items():
		room = room_order[1]
		to_add = []
		count = room.room_person_no
		alreadyPresent = len(room.room_members)
		missing_slots = count - alreadyPresent
		for _ in range(missing_slots):
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
			'to_add': to_add,
			'count': count,
			'previouslyPresent': alreadyPresent
		}
	
	generated_counter = 0
	# Create additional rooms
	while len(roomless_orders.items()) > 0:
		room = list(roomless_orders.items())[0][1]
		to_add = []
		count = room.room_person_no
		alreadyPresent = len(room.room_members)
		missing_slots = count - alreadyPresent
		for _ in range(missing_slots):
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
			'to_add': to_add,
			'count': count,
			'previouslyPresent': alreadyPresent
		}
	
	result_map["infinite"] = { 'to_add': [] }
	result_map = {k: v for k, v in sorted(result_map.items(), key=lambda x: ((x[1]["count"], x[1]["previouslyPresent"]) if("count" in x[1] and "previouslyPresent" in x[1]) else (4316, 0) ))}
	tpl = request.app.ctx.tpl.get_template('wizard.html')
	return html(tpl.render(order=order, all_orders=all_orders, unconfirmed_orders=orders, data=result_map, jsondata=json.dumps(result_map, skipkeys=True, ensure_ascii=False)))

@bp.post('/room/wizard/submit')
async def submit_from_room_wizard(request:Request, order:Order):
	'''Will apply changes to the rooms'''
	await request.app.ctx.om.fill_cache()

	data = json.loads(request.body)

	# Phase 1 - Delete all rooms in void
	if 'void' in data:
		for room_code in data['void']:
			ppl = await get_people_in_room_by_code(request, room_code)
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
		logger.info(f"Deleted rooms {', '.join(data['void'])}")
	
	# Phase 2 - Join roomless to other rooms or add new rooms
	for room_code, value in {key:value for key,value in data.items() if key.lower() not in ['void', 'infinite']}.items():
		if not value['to_add'] or len(value['to_add']) == 0: continue
		room_order = await request.app.ctx.om.get_order(code=room_code)
		# Preconditions
		if not room_order: raise exceptions.BadRequest(f"Order {room_code} does not exist.")
		if room_order.daily == True: raise exceptions.BadRequest(f"Order {room_code} is daily.")
		if room_order.status != 'paid': raise exceptions.BadRequest(f"Order {room_code} hasn't paid.")
		if room_order.room_owner:
			if room_order.room_person_no < len(room_order.room_members) + (len(value['to_add']) if value['to_add'] else 0):
				raise exceptions.BadRequest(f"Input exceeds room {room_order.code} capacity.")
		elif room_order.room_person_no < (len(value['to_add']) if value['to_add'] else 0):
			raise exceptions.BadRequest(f"Input exceeds room {room_order.code} capacity.")
		
		# Adding roomless orders to existing rooms
		if value['type'] == 'add_existing' or value['type'] == 'new':
			if value['type'] == 'new':
				if room_order.room_owner: exceptions.BadRequest(f"Order {room_code} is already a room owner.")
				# Create room data
				await room_order.edit_answer('room_name', value['room_name'])
				await room_order.edit_answer('room_id', room_order.code)
				await room_order.edit_answer('room_secret', ''.join(choice('0123456789') for _ in range(6)))
			elif not room_order.room_owner:
				raise exceptions.BadRequest(f"Order {room_code} is not a room owner.")
			# Add members
			for new_member_code in value['to_add']:
				pending_member = await request.app.ctx.om.get_order(code=new_member_code)
				# Preconditions
				if pending_member.daily == True: raise exceptions.BadRequest(f"Order {pending_member.code} is daily.")
				if pending_member.status != 'paid': raise exceptions.BadRequest(f"Order {new_member_code} hasn't paid.")
				if pending_member.bed_in_room != room_order.bed_in_room: raise exceptions.BadRequest(f"Order {new_member_code} has a different room type than {room_code}.")
				if pending_member.room_owner: exceptions.BadRequest(f"Order {new_member_code} is already a room owner.")
				if pending_member.room_id and pending_member.room_id not in data['void']: exceptions.BadRequest(f"Order {new_member_code} is in another room.")
				await pending_member.edit_answer('room_id', room_order.code)
				await pending_member.edit_answer('room_confirmed', "True")
				await pending_member.edit_answer('pending_room', None)
				await pending_member.send_answers()
			logger.info(f"{'Created' if value['type'] == 'new' else 'Edited'} {str(room_order)}")
			# Confirm members that were already inside the room
			if value['type'] == 'add_existing':
				for already_member in list(filter(lambda rm: rm.code in room_order.room_members and rm.code != room_order.code, request.app.ctx.om.cache.values())):
					await already_member.edit_answer('room_confirmed', "True")
					await already_member.send_answers()
		else: raise exceptions.BadRequest(f"Unexpected type ({value['type']})")
		await room_order.edit_answer('pending_room', None)
		await room_order.edit_answer('pending_roommates', None)
		# await room_order.edit_answer('room_confirmed', "True") Use the autoconfirm button in the admin panel
		await room_order.edit_answer('room_members', ','.join(list(set([*room_order.room_members, room_order.code, *value['to_add']]))))
		await room_order.send_answers()
		await request.app.ctx.om.fill_cache()
	return text('done', status=200)
	

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