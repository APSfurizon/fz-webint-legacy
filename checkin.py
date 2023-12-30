from sanic.response import html, redirect, text
from sanic import Blueprint, exceptions, response
from random import choice
from ext import *
from config import headers, base_url_event
from PIL import Image
from os.path import isfile
from os import unlink
from io import BytesIO
from hashlib import sha224
from time import time
from urllib.parse import unquote
import json

bp = Blueprint("checkin", url_prefix="/checkin")

@bp.get("/")
async def redirect_start(request):
	return response.redirect("start")

@bp.get("/start")
async def start_checkin(request):
	orders = request.app.ctx.om.cache.values()
	tpl = request.app.ctx.tpl.get_template('checkin_1.html')
	return html(tpl.render(orders=orders))
	
@bp.get("/order")
async def show_order(request):

	max_id = 0
	for o in request.app.ctx.om.cache.values():
		if not o.badge_id: continue
		max_id = max(o.badge_id, max_id)

	order = await request.app.ctx.om.get_order(code=request.args.get('order'))
	
	if order.room_id == order.code:
		room_owner = order
	else:
		room_owner = await request.app.ctx.om.get_order(code=order.room_id)
	
	tpl = request.app.ctx.tpl.get_template('checkin_2.html')
	return html(tpl.render(order=order, room_owner=room_owner, max_id=max_id))

@bp.post("/checkin")
async def do_checkin(request):
	
	# Update room info
	order = await request.app.ctx.om.get_order(code=request.form.get('code'))
	if order.room_id == order.code:
		room_owner = order
		await order.edit_answer('actual_room', request.form.get('actual_room'))
	else:
		room_owner = await request.app.ctx.om.get_order(code=order.room_id)
		await room_owner.edit_answer('actual_room', request.form.get('actual_room'))
		await room_owner.send_answers()

	roommates = [await request.app.ctx.om.get_order(code=code, cached=True) for code in room_owner.room_members]

	# Update nfc and badge id
	await order.edit_answer('nfc_id', request.form.get('nfc_id'))
	await order.edit_answer('badge_id', request.form.get('badge_id'))
	await order.send_answers()
	
	if not order.checked_in:
		async with httpx.AsyncClient() as client:
			res = await client.post(base_url_event.replace(f'events/{EVENT_NAME}/', 'checkinrpc/redeem/'), json={'secret': order.barcode, 'source_type': 'barcode', 'type': 'entry', 'lists': [3,]}, headers=headers)
	
	tpl = request.app.ctx.tpl.get_template('checkin_3.html')
	return html(tpl.render(order=order, room_owner=room_owner, roommates=roommates))

	
