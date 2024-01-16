from sanic.response import html, redirect, text
from sanic import Blueprint, exceptions
from random import choice
from ext import *
from config import headers

jobs = []

bp = Blueprint("room", url_prefix="/manage/room")

@bp.post("/create")
async def room_create_post(request, order: Order):
	if not order: raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")

	error = None
	name = request.form.get('name')
	
	if len(name) > 64 or len(name) < 4:
		error = "Your room name is invalid. Please try another one."
		
	if order.room_id:
		error = "You are already in another room. You need to delete (if it's yours) or leave it before creating another."

	if order.daily:
		raise exceptions.BadRequest("You cannot create a room if you have a daily ticket!") 
		
	if not error:
		await order.edit_answer('room_name', name)
		await order.edit_answer('room_id', order.code)
		await order.edit_answer('room_members', order.code)
		await order.edit_answer('room_secret', ''.join(choice('0123456789') for _ in range(6)))
		await order.send_answers()
		return redirect('/manage/welcome')

	tpl = request.app.ctx.tpl.get_template('create_room.html')
	return html(tpl.render(order=order, error=error))

@bp.route("/create")
async def room_create(request, order: Order):

	if not order: raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")

	if order.daily:
		raise exceptions.BadRequest("You cannot create a room if you have a daily ticket!") 

	tpl = request.app.ctx.tpl.get_template('create_room.html')
	return html(tpl.render(order=order))
	
@bp.route("/delete")
async def delete_room(request, order: Order):
	if not order:
		raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")

	if not order.room_owner:
		raise exceptions.BadRequest("You are not allowed to delete room of others.")
		
	if order.ans('room_confirmed'):
		raise exceptions.BadRequest("You are not allowed to change your room after it has been confirmed.")
		
	if len(order.room_members) > 1:
		raise exceptions.BadRequest("You can only delete a room once there is nobody else inside.")

	await order.edit_answer('room_name', None)
	await order.edit_answer('room_id', None)
	await order.edit_answer('room_members', None)
	await order.edit_answer('room_secret', None)
	await order.send_answers()
	return redirect('/manage/welcome')	
	
@bp.post("/join")
async def join_room(request, order: Order):

	if not order:
		raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")

	if order.pending_room:
		raise exceptions.BadRequest("There is already a pending join request. Wait for the room owner to accept or refuse it.")

	if order.room_id:
		raise exceptions.BadRequest("You are in another room already. Why would you join another?")
	
	if order.daily:
		raise exceptions.BadRequest("You cannot join a room if you have a daily ticket!") 

	code = request.form.get('code').strip()
	room_secret = request.form.get('room_secret').strip()
	
	if (not code) or (not room_secret):
		raise exceptions.BadRequest("The code or pin you provided are not valid.")
	
	room_owner = await request.app.ctx.om.get_order(code=code)
	
	if not room_owner:
		raise exceptions.BadRequest("The code you provided is not valid.")

	if room_owner.room_secret != room_secret:
		raise exceptions.BadRequest("The code or pin you provided is not valid.")
		
	if room_owner.room_confirmed:
		raise exceptions.BadRequest("The room you're trying to join has been confirmed already")
	
	if room_owner.bed_in_room != order.bed_in_room:
		raise exceptions.BadRequest("This room's ticket is of a different type than yours!")
		
	#if room_owner.pending_roommates and (order.code in room_owner.pending_roommates):
		#raise exceptions.BadRequest("What? You should never reach this check, but whatever...")

	await order.edit_answer('pending_room', code)
	await order.send_answers()
	
	pending_roommates = room_owner.pending_roommates
	if not order.code in pending_roommates:
		pending_roommates.append(order.code)
	
	await room_owner.edit_answer('pending_roommates', ','.join(pending_roommates))
	await room_owner.send_answers()
	
	return redirect('/manage/welcome')

@bp.route("/kick/<code>")
async def kick_member(request, code, order: Order):
	if not order:
		raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")
	
	if order.room_confirmed:
		raise exceptions.BadRequest("You cannot kick people out of confirmed rooms")

	if not order.room_owner:
		raise exceptions.BadRequest("You cannot kick people if you're not the room owner")
		
	to_kick = await request.app.ctx.om.get_order(code=code)
	if to_kick.room_id != order.code:
		raise exceptions.BadRequest("You cannot kick people of other rooms")
		
	await to_kick.edit_answer('room_id', None)
	await order.edit_answer('room_members', ','.join([x for x in order.room_members if x != to_kick.code]) or None)

	await order.send_answers()	
	await to_kick.send_answers()
	
	return redirect('/manage/welcome')

@bp.route("/renew_secret")
async def renew_secret(request, order: Order):
	if not order:
		raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")

	if not order.room_id:
		raise exceptions.BadRequest("What room were you even trying to renew?")
		
	if not order.room_owner:
		raise exceptions.BadRequest("You are not allowed to renew rooms of others.")
		
	await order.edit_answer('room_secret', ''.join(choice('0123456789') for _ in range(6)))
	await order.send_answers()
	return redirect('/manage/welcome')
	
@bp.route("/cancel_request")
async def cancel_request(request, order: Order):
	if not order:
		raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")

	if not order.pending_room:
		raise exceptions.BadRequest("There is no pending room.")
		
	room_owner = await request.app.ctx.om.get_order(code=order.pending_room)
	pending_roommates = room_owner.pending_roommates
	if order.code in pending_roommates:
		pending_roommates.remove(order.code)
		await room_owner.edit_answer('pending_roommates', ','.join(pending_roommates) if pending_roommates else None)
		await room_owner.send_answers()
		
	await order.edit_answer('pending_room', None)
	await order.send_answers()
	return redirect('/manage/welcome')
	
@bp.route("/approve/<code>")
async def approve_roomreq(request, code, order: Order):
	if not order:
		raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")
	
	if not order.room_owner:
		raise exceptions.BadRequest("You are not the owner of the room!")
		
	if not code in order.pending_roommates:
		raise exceptions.BadRequest("You cannot accept people that didn't request to join your room")

	if order.room_confirmed:
		raise exceptions.BadRequest("You cannot accept people to a confirmed room.")

	pending_member = await request.app.ctx.om.get_order(code=code)

	if pending_member.room_id:
		raise exceptions.BadRequest("You cannot accept people who are in a room.")
	
	if pending_member.pending_room != order.code:
		raise exceptions.BadRequest("You cannot accept people who are in another room or waiting to accept another request.")
		
	await pending_member.edit_answer('room_id', order.code)
	await pending_member.edit_answer('pending_room', None)
	
	await order.edit_answer('room_members', ','.join([*order.room_members, pending_member.code]))
	await order.edit_answer('pending_roommates', (','.join([x for x in order.pending_roommates if x != pending_member.code]) or None))
	
	await pending_member.send_answers()
	await order.send_answers()
	
	return redirect('/manage/welcome')
	
@bp.route("/leave")
async def leave_room(request, order: Order):
	if not order:
		raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")

	if not order.room_id:
		raise exceptions.BadRequest("You cannot leave a room without being in it.")

	if order.room_confirmed:
		raise exceptions.BadRequest("You cannot leave a confirmed room.")
		
	if order.room_id == order.code:
		raise exceptions.BadRequest("You cannot leave your own room.")

	room_owner = await request.app.ctx.om.get_order(code=order.room_id)
	
	await room_owner.edit_answer('room_members', (','.join([x for x in room_owner.room_members if x != order.code]) or None))
	await order.edit_answer('room_id', None)
		
	await room_owner.send_answers()
	await order.send_answers()
	
	return redirect('/manage/welcome')

@bp.route("/reject/<code>")
async def reject_roomreq(request, code, order: Order):
	if not order:
		raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")
	
	if not order.room_owner:
		raise exceptions.BadRequest("You are not the owner of the room!")
		
	if not code in order.pending_roommates:
		raise exceptions.BadRequest("You cannot reject people that didn't request to join your room")

	if order.room_confirmed:
		raise exceptions.BadRequest("You cannot reject people to a confirmed room.")

	pending_member = await request.app.ctx.om.get_order(code=code)

	if pending_member.room_id:
		raise exceptions.BadRequest("You cannot reject people who are in a room.")
	
	if pending_member.pending_room != order.code:
		raise exceptions.BadRequest("You cannot reject people who are in another room or waiting to accept another request.")

	await pending_member.edit_answer('pending_room', None)
	await order.edit_answer('pending_roommates', (','.join([x for x in order.pending_roommates if x != pending_member.code]) or None))
	
	await pending_member.send_answers()
	await order.send_answers()
	
	return redirect('/manage/welcome')

@bp.post("/rename")
async def rename_room(request, order: Order):
	if not order:
		raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")
	
	if not order.room_owner:
		raise exceptions.BadRequest("You are not the owner of the room!")
		
	if not order.room_id:
		raise exceptions.BadRequest("Try joining a room before renaming it.")

	if order.room_confirmed:
		raise exceptions.BadRequest("You can't rename a confirmed room!")
	
	if order.room_id != order.code:
		raise exceptions.BadRequest("You are not allowed to rename rooms of others.")

	name = request.form.get('name')
	if len(name) > 64 or len(name) < 4:
		raise exceptions.BadRequest("Your room name is invalid. Please try another one.")

	await order.edit_answer("room_name", name)
	await order.send_answers()

	return redirect('/manage/welcome')
	
@bp.route("/confirm")
async def confirm_room(request, order: Order, quotas: Quotas):
	if not order:
		raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")
		
	if not order.room_id:
		raise exceptions.BadRequest("Try joining a room before confirming it.")
		
	if order.room_id != order.code:
		raise exceptions.BadRequest("You are not allowed to confirm rooms of others.")

	# This is not needed anymore you buy tickets already 
	#if quotas.get_left(len(order.room_members)) == 0:
	#	raise exceptions.BadRequest("There are no more rooms of this size to reserve.")

	bed_in_room = order.bed_in_room # Variation id of the ticket for that kind of room
	room_members = []
	for m in order.room_members:
		if m == order.code:
			res = order
		else:
			res = await request.app.ctx.om.get_order(code=m)
		
		if res.room_id != order.code:
			raise exceptions.BadRequest("Please contact support: some of the members in your room are actually somewhere else")	
		
		if res.status != 'paid':
			raise exceptions.BadRequest("Somebody hasn't paid.")
		
		if res.bed_in_room != bed_in_room:
			raise exceptions.BadRequest("Somebody has a ticket for a different type of room!")
		
		if res.daily:
			raise exceptions.BadRequest("Somebody in your room has a daily ticket!") 
			
		room_members.append(res)
	

	if len(room_members) != order.room_person_no and order.room_person_no != None:
		raise exceptions.BadRequest("The number of people in your room mismatches your type of ticket!")

	for rm in room_members:
		await rm.edit_answer('room_id', order.code)
		await rm.edit_answer('room_confirmed', "True")
		await rm.edit_answer('pending_roommates', None)
		await rm.edit_answer('pending_room', None)
	
	# This should now be useless because in the ticket there already is the ticket/room type
	# thing = {
	# 	'order': order.code,
	# 	'addon_to': order.position_positionid,
	# 	'item': ITEM_IDS['room'],
	# 	'variation': ROOM_MAP[len(room_members)]
	# }
	# 
	# async with httpx.AsyncClient() as client:
	# 	res = await client.post(join(base_url_event, "orderpositions/"), headers=headers, json=thing)
	# 	
	# 	if res.status_code != 201:
	# 		raise exceptions.BadRequest("Something has gone wrong! Please contact support immediately")
	
	for rm in room_members:
		await rm.send_answers()

	return redirect('/manage/welcome')

async def get_room (request, code):
	order_data = await request.app.ctx.om.get_order(code=code)
	if not order_data or not order_data.room_owner: return None
	members_map = []
	for member_code in order_data.room_members:
		member_order = await request.app.ctx.om.get_order(code=member_code)
		if not member_order: continue
		members_map.append ({'name': member_order.name, 'propic': member_order.propic, 'sponsorship': member_order.sponsorship})
	return {'name': order_data.room_name, 'members': members_map}



@bp.route("/view/<code>")
async def get_view(request, code):
	if code in jobs:
		raise exceptions.SanicException("The room's preview is being generated... Wait a little longer", status_code=409)
	jobs.append(code)
	try:
		room_data = await get_room(request, code)
		return room_data
	except Exception:
		# Remove fault job
		if len(jobs) > 0: jobs.pop()
		raise exceptions.SanicException("Could not get that room's data at the moment. Try again, later.", status_code=500)
	finally:
		# Remove fault job
		if len(jobs) > 0: jobs.pop()
	if not room_data:
		raise exceptions.SanicException("There's no room with that code.", status_code=404)