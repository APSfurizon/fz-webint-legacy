from sanic import Blueprint, exceptions, response
from time import time
from asyncio import Future
import asyncio
from datetime import datetime
from asyncio import Queue
from random import randint
from boop_process import boop_process

bp = Blueprint("boop", url_prefix="/boop")

bp.ctx.boopbox_queue = {'a': Queue(), 'b': Queue(), 'c': Queue()}
bp.ctx.busy = {'a': False, 'b': False, 'c': False}
bp.ctx.last_tag = {'a': None, 'b': None, 'c': None}
bp.ctx.repeats = {'a': None, 'b': None, 'c': None}

def enable_nfc(enable, boopbox_id):	
	log.info('NFC is ' + ('enabled' if enable else 'disabled'))
	app.ctx.queue.put_nowait({'_': 'nfc', 'enabled': enable})
	app.ctx.nfc_enabled = enable;

@bp.get("/refresh")
async def refresh_boops(request):
	await boop_process(request.app.ctx.om.cache.values(), request.app.ctx.boop)
	return response.text('ok')

@bp.get("/")
async def show_boopbox(request):
	tpl = request.app.ctx.tpl.get_template('boopbox.html')
	return response.html(tpl.render())
	
@bp.get("/getqueue/<boopbox_id>")
async def boop_queue(request, boopbox_id):
	
	items = []
	queue = bp.ctx.boopbox_queue[boopbox_id]
	while 1:
		try:
			item = queue.get_nowait()
		except asyncio.queues.QueueEmpty:
			if items:
				break
				
			# Try one last time to get a task, then fail.
			bp.ctx.busy[boopbox_id] = False
			try:
				item = await asyncio.wait_for(queue.get(), timeout=5)
			except asyncio.exceptions.TimeoutError:
				break

		items.append(item)

	if len(items):
		bp.ctx.busy[boopbox_id] = True	
	return response.json(items)

@bp.post("/read")
async def handle_boop(request):
	payload = request.json
	queue = bp.ctx.boopbox_queue[payload['boopbox_id']]

	if bp.ctx.busy[payload['boopbox_id']]: return response.text('busy')
	
	
	await queue.put({'_': 'play', 'src': f"/res/snd/error.wav"})
	
	if bp.ctx.last_tag[payload['boopbox_id']] == payload['id']:
		bp.ctx.repeats[payload['boopbox_id']] += 1
	else:
		bp.ctx.last_tag[payload['boopbox_id']] = payload['id']
		bp.ctx.repeats[payload['boopbox_id']] = 0
		
	if bp.ctx.repeats[payload['boopbox_id']] > 5:
		await queue.put({'_': 'play', 'src': f"/res/snd/ratelimit.wav"})
		await queue.put({'_': 'bye'})
		return response.text('ok')
		
	if bp.ctx.repeats[payload['boopbox_id']] > 10:
		await queue.put({'_': 'talk', 'who': 'tiger', 'msg': f"Hey! Stop that! You're not the only one here!"})
		await queue.put({'_': 'bye'})
		return response.text('ok')
	
	request.app.ctx.boop.execute('INSERT INTO boop(tag_id, station, ts) VALUES (?,?,?)', (payload['id'], payload['boopbox_id'], int(time())))
	request.app.ctx.boop.commit()
	
	return response.text('ok')
