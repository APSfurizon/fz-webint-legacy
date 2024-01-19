from sanic.response import html, redirect, text
from sanic import Blueprint, exceptions
from random import choice
from ext import *
from config import headers
from PIL import Image, ImageDraw, ImageFont
import textwrap
import os

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
	remove_room_preview (order.code)
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
	remove_room_preview (code)
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
	remove_room_preview (order.code)
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
	await order.send_answers(order.code)
	remove_room_preview()
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
	remove_room_preview (order.room_id)
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
	remove_room_preview(order.code)
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
	members_map = [{'name': order_data.name, 'propic': order_data.propic, 'sponsorship': order_data.sponsorship}]
	for member_code in order_data.room_members:
		if member_code == order_data.code: continue
		member_order = await request.app.ctx.om.get_order(code=member_code)
		if not member_order: continue
		members_map.append ({'name': member_order.name, 'propic': member_order.propic, 'sponsorship': member_order.sponsorship})
	return {'name': order_data.room_name, 
		 	'confirmed': order_data.room_confirmed,
			'capacity': order_data.room_person_no,
			'free_spots': order_data.room_person_no - len(members_map),
			'members': members_map}

async def get_room_with_order (request, code):
	order_data = await request.app.ctx.om.get_order(code=code)
	if not order_data or not order_data.room_owner: return None

def remove_room_preview(code):
	preview_file = f"res/rooms/{code}.jpg"
	try:
		if os.path.exists(preview_file): os.remove(preview_file)
	except Exception as ex:
		if (EXTRA_PRINTS): print(ex)

def draw_profile (source, member, position, font, size=(170, 170), border_width=5):
	idraw = ImageDraw.Draw(source)
	source_size = source.size
	main_fill = (187, 198, 206)
	propic_x = position[0]
	propic_y = (source_size[1] // 2) - (size[1] // 2)
	border_loc = (propic_x, propic_y, propic_x + size[0] + border_width * 2, propic_y + size[1] + border_width *2)
	profile_location = (propic_x + border_width, propic_y + border_width)
	propic_name_y = propic_y + size[1] + border_width + 20
	border_color = SPONSORSHIP_COLOR_MAP[member['sponsorship']] if member['sponsorship'] in SPONSORSHIP_COLOR_MAP.keys() else (84, 110, 122)
	# Draw border
	idraw.rounded_rectangle(border_loc, border_width, border_color)
	# Draw profile picture
	with Image.open(f'res/propic/{member['propic'] or 'default.png'}') as to_add:
		source.paste(to_add.resize (size), profile_location)
	name_len = idraw.textlength(str(member['name']), font)
	calc_size = 0
	if name_len > size[0]:
		calc_size = size[0] * 20 / name_len if name_len > size[0] else 20
		font = ImageFont.truetype(font.path, calc_size)
		name_len = idraw.textlength(str(member['name']), font)
	name_loc = (position[0] + ((size[0] / 2) - name_len / 2), propic_name_y + (calc_size/2))
	name_color = SPONSORSHIP_COLOR_MAP[member['sponsorship']] if member['sponsorship'] in SPONSORSHIP_COLOR_MAP.keys() else main_fill
	idraw.text(name_loc, str(member['name']), font=font, fill=name_color)

async def generate_room_preview(request, code, room_data):
	font_path = f'res/font/NotoSans-Bold.ttf'
	main_fill = (187, 198, 206)
	propic_size = (170, 170)
	logo_size = (200, 43)
	border_width = 5
	propic_gap = 50
	propic_width = propic_size[0] + (border_width * 2)
	propic_total_width = propic_width + propic_gap
	jobs.append(code)
	try:
		room_data = await get_room(request, code) if not room_data else room_data
		if not room_data: return
		width = max([(propic_width + propic_gap) * int(room_data['capacity']) + propic_gap, 670])
		height = int(width * 0.525)
		font = ImageFont.truetype(font_path, 20)

		# Recalculate gap
		propic_gap = (width - (propic_width * int(room_data['capacity']))) // (int(room_data['capacity']) + 1)
		propic_total_width = propic_width + propic_gap

		# Define output image
		with Image.new('RGB', (width, height), (17, 25, 31)) as source:
			# Draw logo
			with (Image.open('res/furizon.png') as logo, logo.resize(logo_size).convert('RGBA') as resized_logo):
				source.paste(resized_logo, ((source.size[0] // 2) - (logo_size[0] // 2), 10), resized_logo)
			i_draw = ImageDraw.Draw(source)
			# Draw room's name
			room_name_len = i_draw.textlength(room_data['name'], font)
			i_draw.text((((width / 2) - room_name_len / 2), 55), room_data['name'], font=font, fill=main_fill)
			# Draw members
			for m in range (room_data['capacity']):
				member = room_data['members'][m] if m < len(room_data['members']) else { 'name': 'Empty', 'propic': '../new.png', 'sponsorship': None }
				font = ImageFont.truetype(font_path, 20)
				draw_profile(source, member, (propic_gap + (propic_total_width * m), 63), font, propic_size, border_width)
			source.save(f'res/rooms/{code}.jpg', 'JPEG', quality=60)
	except Exception as err:
		if EXTRA_PRINTS: print(err)
	finally:
		# Remove fault job
		if len(jobs) > 0: jobs.pop()
	if not room_data:
		raise exceptions.SanicException("There's no room with that code.", status_code=404)

@bp.route("/view/<code>")
async def get_view(request, code):
	room_file_name = f"res/rooms/{code}.jpg"
	room_data = await get_room(request, code)

	if not os.path.exists(room_file_name) and code not in jobs:
		await generate_room_preview(request, code, room_data)
	tpl = request.app.ctx.tpl.get_template('view_room.html')
	return html(tpl.render(preview=room_file_name, room_data=room_data))
	