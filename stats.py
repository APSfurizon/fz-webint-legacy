from sanic.response import html
from sanic import Blueprint, exceptions
from ext import *
from config import headers
from time import time
import asyncio

bp = Blueprint("stats", url_prefix="/manage")

def by_count(d):
	return {k:v for k,v in sorted(d.items(), key=lambda x: x[1], reverse=True)}

async def gen_stats(app):
	orders = app.ctx.om.cache.values()
	
	countries = {}
	sponsors = {}
	
	for o in orders:
		countries[o.country] = countries.get(o.country, 0) +1
		sponsors[o.sponsorship or 'no'] = sponsors.get(o.sponsorship or 'no', 0) +1

	app.ctx.stats = {
		'countries': by_count(countries),
		'sponsors': by_count(sponsors),
		'time': time()
	}
	
	return app.ctx.stats

@bp.route("/stats")
async def stats(request, order: Order):

	stats = getattr(request.app.ctx, 'stats', None)
	'''if not stats:
		await gen_stats(request.app)
	elif time() - stats['time'] > 1800:
		asyncio.create_task(gen_stats(request.app))'''
	
	request.app.ctx.stats = await gen_stats(request.app)
	
	tpl = request.app.ctx.tpl.get_template('stats.html')
	return html(tpl.render(order=order, stats=request.app.ctx.stats))

@bp.route("/nosecount")
async def nose_count(request, order: Order):
	orders = {key:value for key,value in sorted(request.app.ctx.om.cache.items(), key=lambda x: len(x[1].room_members), reverse=True) if value.status not in ['c', 'e']}

	tpl = request.app.ctx.tpl.get_template('nosecount.html')
	return html(tpl.render(orders=orders, order=order))
