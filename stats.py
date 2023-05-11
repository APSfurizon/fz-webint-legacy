from sanic.response import html
from sanic import Blueprint, exceptions
from ext import *
from config import headers
from time import time
import asyncio

bp = Blueprint("stats", url_prefix="/manage")

@bp.route("/nosecount")
async def nose_count(request, order: Order):
	orders = {key:value for key,value in sorted(request.app.ctx.om.cache.items(), key=lambda x: len(x[1].room_members), reverse=True) if value.status not in ['c', 'e']}

	tpl = request.app.ctx.tpl.get_template('nosecount.html')
	return html(tpl.render(orders=orders, order=order))
