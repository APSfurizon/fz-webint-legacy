from sanic import Blueprint, exceptions, response
from random import choice
from ext import *
from config import headers, PROPIC_DEADLINE
from PIL import Image
from os.path import isfile
from os import unlink
from io import BytesIO
from hashlib import sha224
from time import time
from urllib.parse import unquote
from base64 import b16decode
from asyncio import Future
import json
import re
import asyncio

bp = Blueprint("nfc")
	
@bp.post("/nfc/read")
async def handle_reading(request):
	payload = request.json
	if payload['count']:
		request.app.ctx.nfc_counts.execute('INSERT INTO read_count(tag_id, ts, count) VALUES (?,?,?)', (payload['id'], int(time()), payload['count']))
		request.app.ctx.nfc_counts.commit()
		
	if payload['boopbox_id']:
		await request.app.ctx.boopbox_queue.put(payload)
		return response.text('ok')

	if not request.ip in request.app.ctx.nfc_reads:
		return response.text('wasted read')

	try:
		request.app.ctx.nfc_reads[request.ip].set_result(payload)
	except asyncio.exceptions.InvalidStateError:
		del request.app.ctx.nfc_reads[request.ip]
	
	return response.text('ok')

@bp.get("/fz23/<tag_id:([bc][0-9A-F]{14}x[0-9A-F]{6})>")
async def handle_nfc_tag(request, tag_id):

	tag = re.match('([bc])([0-9A-F]{14})x([0-9A-F]{6})', tag_id)
	
	# Store the read count
	read_count = int.from_bytes(b16decode(tag.group(3)))
	request.app.ctx.nfc_counts.execute('INSERT INTO read_count(tag_id, ts, count, is_web) VALUES (?,?,?,1)', (tag.group(2), int(time()), read_count))
	request.app.ctx.nfc_counts.commit()

	# If it's a coin, just show the coin template	
	if tag.group(1) == 'c':
		return response.redirect(f"coin/{tag.group(2)}")
	
	# If it's a badge, look for the corresponding order
	for o in request.app.ctx.om.cache.values():
		if o.nfc_id == tag.group(2):
			return response.redirect(o.code)
	
	raise exceptions.NotFound("Unknown tag :(")
	
@bp.get("/fz23/coin/<tag_id>")
async def show_coin(request, tag_id):
	balance = request.app.ctx.money.execute('SELECT sum(amount) FROM tx WHERE tag_id = ?', (tag_id,)).fetchone()[0]

	tpl = request.app.ctx.tpl.get_template('coin.html')
	return response.html(tpl.render(balance=balance))
	
@bp.get("/fz23/<code:[A-Z0-9]{5}>")
async def show_order(request, code):
	return response.html(f"<h1>Badge</h1><p>{code}</p>")
	
