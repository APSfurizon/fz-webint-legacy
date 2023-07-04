from sanic import Blueprint, exceptions, response
from time import time
from asyncio import Future
import asyncio
from datetime import datetime

bp = Blueprint("money", url_prefix="/money")

@bp.post("/pos")
async def do_transaction(request):

	message = ''
	tx_id = request.app.ctx.money.execute('INSERT INTO tx(tag_id, amount, ts) VALUES (?,?,?) RETURNING id', (request.form.get('nfc_id'), request.form.get('total'), time())).fetchone()[0]
	
	for item, qty in request.form.items():
		if not item.startswith('itm_'): continue
		if qty[0] == '0': continue		
		request.app.ctx.money.execute('INSERT INTO tx_items(tx_id, item_id, qty) VALUES (?,?,?)', (tx_id, item[4:], qty[0]))

	request.app.ctx.money.commit()
	return await show_transactions(request, message='Transazione eseguita con successo!')

@bp.get("/pos")
async def show_transactions(request, message=None):
	tpl = request.app.ctx.tpl.get_template('pos.html')
	items = request.app.ctx.money.execute('SELECT * FROM item')
	
	tx_info = {}
	last_tx = request.app.ctx.money.execute('SELECT * FROM tx WHERE amount < 0 ORDER BY ts DESC LIMIT 3').fetchall()
	for tx in last_tx:
		tx_info[tx['id']] = {'items': request.app.ctx.money.execute('SELECT * FROM tx_items JOIN item ON item_id = item.id AND tx_id = ?', (tx['id'],)).fetchall(), 'order': await request.app.ctx.om.get_order(nfc_id=tx['tag_id']), 'time': datetime.fromtimestamp(tx['ts'] or 0).strftime('%H:%M')}
	
	return response.html(tpl.render(items=items, message=message, last_tx=last_tx, tx_info=tx_info))

@bp.get("/poll_barcode")
async def give_barcode(request):

	request.app.ctx.nfc_reads[request.ip] = Future()
	
	try:
		bcd = await asyncio.wait_for(request.app.ctx.nfc_reads[request.ip], 20)
	except asyncio.TimeoutError:
		if not request.ip in request.app.ctx.nfc_reads:
			del request.app.ctx.nfc_reads[request.ip]
		return response.json({'error': 'no_barcode'})

	info = request.app.ctx.money.execute("SELECT count(*), coalesce(sum(amount), 0) FROM tx WHERE coalesce(is_canceled, 0) != 1 AND tag_id = ?", (bcd['id'],)).fetchone()
	
	order = await request.app.ctx.om.get_order(nfc_id=bcd['id'])

	desc = ("⚠️" if not bcd['is_secure'] else '') + (f"👤 {order.code} {order.name}" if order else f"🪙 {bcd['id']}") + f" · Transazioni: {info[0]}"

	return response.json({**bcd, 'txamt': info[0], 'balance': info[1], 'desc': desc})
