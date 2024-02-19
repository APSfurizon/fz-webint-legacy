from sanic.response import html
from sanic import Blueprint, Request
from messages import NOSECOUNT
from ext import *

bp = Blueprint("stats", url_prefix="/manage")

@bp.route("/sponsorcount")
async def sponsor_count(request, order: Order):
	await request.app.ctx.om.update_cache()
	orders = {key:value for key,value in sorted(request.app.ctx.om.cache.items(), key=lambda x: x[1].ans('fursona_name')) if value.status not in ['c', 'e']}

	tpl = request.app.ctx.tpl.get_template('sponsorcount.html')
	return html(tpl.render(orders=orders, order=order))

def calc_filter(orders: dict, filter_cmd: str, order: Order) -> tuple[dict, str]:
	if not filter_cmd or len(filter_cmd) == 0 or not orders or len(orders.keys()) == 0: return
	if filter_cmd.lower() == "capacity":
		return {key:value for key,value in orders.items() if (not value.room_confirmed and value.bed_in_room == order.bed_in_room)}, NOSECOUNT['filters'][filter_cmd.lower()]
	else:
		return None, None

@bp.route("/nosecount")
async def nose_count(request: Request, order: Order):
	await request.app.ctx.om.update_cache()
	orders = {key:value for key,value in sorted(request.app.ctx.om.cache.items(), key=lambda x: len(x[1].room_members), reverse=True) if value.status not in ['c', 'e']}
	filtered: dict = None
	filter_message: str = None
	for query in request.query_args:
		if query[0] == "filter" and order:
			filtered, filter_message = calc_filter(orders, query[1], order) if filter else None
	tpl = request.app.ctx.tpl.get_template('nosecount.html')
	return html(tpl.render(orders=orders, order=order, filtered=filtered, filter_header=filter_message))

@bp.route("/fursuitcount")
async def fursuit_count(request, order: Order):
	await request.app.ctx.om.update_cache()
	orders = {key:value for key,value in sorted(request.app.ctx.om.cache.items(), key=lambda x: x[1].ans('fursona_name')) if value.status not in ['c', 'e']}

	tpl = request.app.ctx.tpl.get_template('fursuitcount.html')
	return html(tpl.render(orders=orders, order=order))