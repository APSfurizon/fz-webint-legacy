from sanic.response import html, redirect, text
from sanic import Blueprint, exceptions
from random import choice
from ext import *
from config import headers

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

	tpl = request.app.ctx.tpl.get_template('create_room.html')
	return html(tpl.render(order=order))
	
@bp.route("/delete")
async def delete_room(request, order: Order):
	if not order:
		raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")

	if order.room_id != order.code:
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
	
@bp.route("/confirm")
async def confirm_room(request, order: Order, quotas: Quotas):
	if not order:
		raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")
		
	if not order.room_id:
		raise exceptions.BadRequest("Try joining a room before confirming it.")
		
	if order.room_id != order.code:
		raise exceptions.BadRequest("You are not allowed to confirm rooms of others.")

	if quotas.get_left(len(order.room_members)) == 0:
		raise exceptions.BadRequest("There are no more rooms of this size to reserve.")

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
			
		room_members.append(res)

	for rm in room_members:
		await rm.edit_answer('room_id', order.code)
		await rm.edit_answer('room_confirmed', "True")
		await rm.edit_answer('pending_roommates', None)
		await rm.edit_answer('pending_room', None)
	
	thing = {
		'order': order.code,
		'addon_to': order.position_positionid,
		'item': ITEM_IDS['room'],
		'variation': ROOM_MAP[len(room_members)]
	}
	
	async with httpx.AsyncClient() as client:
		res = await client.post(join(base_url, "orderpositions/"), headers=headers, json=thing)
		
		if res.status_code != 201:
			raise exceptions.BadRequest("Something has gone wrong! Please contact support immediately")
			
		'''for rm in room_members:
			if rm.code == order.code: continue
			thing = {
				'order': rm.code,
				'addon_to': rm.position_positionid,
				'item': ITEM_IDS['room'],
				'variation': ROOM_MAP[len(room_members)]
			}
			res = await client.post(join(base_url, "orderpositions/"), headers=headers, json=thing)		'''	
	
	for rm in room_members:
		await rm.send_answers()

	return redirect('/manage/welcome')
