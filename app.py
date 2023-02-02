from sanic import Sanic, response, exceptions
from sanic.response import text, html, redirect, raw
from jinja2 import Environment, FileSystemLoader
from time import time
import httpx
import re
import json
from os.path import join
from ext import *
from config import *
from aztec_code_generator import AztecCode
from io import BytesIO

app = Sanic(__name__)
app.static("/res", "res/")

app.ext.add_dependency(Order, get_order)
app.ext.add_dependency(Quotas, get_quotas)

from room import bp as room_bp
from propic import bp as propic_bp
from export import bp as export_bp
from stats import bp as stats_bp

app.blueprint([room_bp,propic_bp,export_bp,stats_bp])

@app.exception(exceptions.SanicException)
async def clear_session(request, exception):
	tpl = app.ctx.tpl.get_template('error.html')
	response = html(tpl.render(exception=exception))
	
	if exception.status_code == 403:
		del response.cookies["foxo_code"]
		del response.cookies["foxo_secret"]
	return response

@app.before_server_start
async def main_start(*_):
	print(">>>>>> main_start <<<<<<")
	
	app.ctx.om = OrderManager()
	app.ctx.tpl = Environment(loader=FileSystemLoader("tpl"), autoescape=True)
	app.ctx.tpl.globals.update(time=time)
	app.ctx.tpl.globals.update(int=int)
	app.ctx.tpl.globals.update(len=len)

@app.route("/manage/barcode/<code>")
async def gen_barcode(request, code):
	aa = AztecCode(code).image(module_size=8, border=2)
	img = BytesIO()
	aa.save(img, format='PNG')

	return raw(img.getvalue(), content_type="image/png")

@app.route("/furizon/beyond/order/<code>/<secret>/open/<secret2>")
async def redirect_explore(request, code, secret, order: Order, secret2=None):

	response = redirect(app.url_for("welcome"))
	if order and order.code != code: order = None

	if not order:
		async with httpx.AsyncClient() as client:
			res = await client.get(join(base_url, f"orders/{code}/"), headers=headers)
			if res.status_code != 200:
				raise exceptions.NotFound("This order code does not exist. Check that your order wasn't deleted, or the link is correct.")
			
			res = res.json()
			if secret != res['secret']:
				raise exceptions.Forbidden("The secret part of the url is not correct. Check your E-Mail for the correct link, or contact support!")
			response.cookies['foxo_code'] = code
			response.cookies['foxo_secret'] = secret
	return response

@app.route("/manage/privacy")
async def privacy(request):
	tpl = app.ctx.tpl.get_template('privacy.html')
	return html(tpl.render())

@app.route("/manage/welcome")
async def welcome(request, order: Order, quota: Quotas):

	if not order:
		raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")

	pending_roommates = []
	if order.pending_roommates:
		for pr in order.pending_roommates:
			if not pr: continue
			pending_roommates.append(await app.ctx.om.get_order(code=pr, cached=True))

	room_members = []
	if order.room_id:
		if order.room_id != order.code:
			room_owner = await app.ctx.om.get_order(code=order.room_id, cached=True)
		else:
			room_owner = order
			
		room_members.append(room_owner)
			
		for member_id in room_owner.ans('room_members').split(','):
			if member_id == room_owner.code: continue
			if member_id == order.code:
				room_members.append(order)
			else:
				room_members.append(await app.ctx.om.get_order(code=member_id, cached=True))		

	tpl = app.ctx.tpl.get_template('welcome.html')
	return html(tpl.render(order=order, quota=quota, room_members=room_members, pending_roommates=pending_roommates))


@app.route("/manage/download_ticket")
async def download_ticket(request, order: Order):

	if not order:
		raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")
		
	if not order.status != 'confirmed':
		raise exceptions.Forbidden("You are not allowed to download this ticket.")
		
	async with httpx.AsyncClient() as client:
		res = await client.get(join(base_url, f"orders/{order.code}/download/pdf/"), headers=headers)
	
	if res.status_code == 409:
		raise exceptions.SanicException("Your ticket is still being generated. Please try again later!", status_code=res.status_code)
	elif res.status_code == 403:
		raise exceptions.SanicException("You can download your ticket only after the order has been confirmed and paid. Try later!", status_code=400)

	return raw(res.content, content_type='application/pdf')
	
@app.route("/manage/logout")
async def logour(request):
	raise exceptions.Forbidden("You have been logged out.", status_code=403)

if __name__ == "__main__":
	app.run(host="0.0.0.0", port=8188, dev=DEV_MODE)
