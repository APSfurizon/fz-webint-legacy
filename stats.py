from sanic.response import html
from sanic import Blueprint
from ext import *

bp = Blueprint("stats", url_prefix="/manage")

@bp.route("/sponsorcount")
async def sponsor_count(request, order: Order):
	await request.app.ctx.om.updateCache()
	orders = {key:value for key,value in sorted(request.app.ctx.om.cache.items(), key=lambda x: len(x[1].room_members), reverse=True) if value.status not in ['c', 'e']}

	tpl = request.app.ctx.tpl.get_template('sponsorcount.html')
	return html(tpl.render(orders=orders, order=order))

@bp.route("/nosecount")
async def nose_count(request, order: Order):
	await request.app.ctx.om.updateCache()
	orders = {key:value for key,value in sorted(request.app.ctx.om.cache.items(), key=lambda x: len(x[1].room_members), reverse=True) if value.status not in ['c', 'e']}

	tpl = request.app.ctx.tpl.get_template('nosecount.html')
	return html(tpl.render(orders=orders, order=order))

@bp.route("/fursuitcount")
async def fursuit_count(request, order: Order):
	await request.app.ctx.om.updateCache()
	orders = {key:value for key,value in sorted(request.app.ctx.om.cache.items(), key=lambda x: len(x[1].room_members), reverse=True) if value.status not in ['c', 'e']}

	tpl = request.app.ctx.tpl.get_template('fursuitcount.html')
	return html(tpl.render(orders=orders, order=order))