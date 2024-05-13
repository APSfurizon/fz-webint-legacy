from sanic import Sanic, response, exceptions
from sanic.response import text, html, redirect, raw
from jinja2 import Environment, FileSystemLoader
from time import time, sleep
import httpx
from os.path import join
from ext import *
from config import *
from aztec_code_generator import AztecCode
from propic import resetDefaultPropic
from io import BytesIO
from asyncio import Queue
from messages import LOCALES
import sqlite3
import requests
import sys
from sanic.log import logger, logging, access_logger
from metrics import *
from email_util import killSmptClient
import pretixClient
import traceback

app = Sanic(__name__)
app.static("/res", "res/")

app.ext.add_dependency(Order, get_order)
app.ext.add_dependency(Quotas, get_quotas)

from room import bp as room_bp
from propic import bp as propic_bp
from karaoke import bp as karaoke_bp
from stats import bp as stats_bp
from api import bp as api_bp
from carpooling import bp as carpooling_bp
from checkin import bp as checkin_bp
from admin import bp as admin_bp

app.blueprint([room_bp, karaoke_bp, propic_bp, stats_bp, api_bp, carpooling_bp, checkin_bp, admin_bp])


async def clear_session(response):
	response.delete_cookie("foxo_code")
	response.delete_cookie("foxo_secret")

@app.exception(exceptions.SanicException if DEV_MODE else Exception)
async def handleException(request, exception):
	incErrorNo()
	logger.warning(f"{request} -> {exception}")
	statusCode = exception.status_code if hasattr(exception, 'status_code') else 500
	try:
		tpl = app.ctx.tpl.get_template('error.html')
		r = html(tpl.render(exception=exception, status_code=statusCode))
	except:
		traceback.print_exc()

	if statusCode == 403:
		await clear_session(r)
	return r


@app.before_server_start
async def main_start(*_):
	logger.info(f"[{app.name}] >>>>>> main_start <<<<<<")
	logger.setLevel(LOG_LEVEL)
	access_logger.addFilter(MetricsFilter())

	app.config.REQUEST_MAX_SIZE = PROPIC_MAX_FILE_SIZE * 3
	
	app.ctx.om = OrderManager()
	if FILL_CACHE:
		checked, success = await app.ctx.om.update_cache(check_itemsQuestions=True)
		if checked and not success:
			logger.error(f"[{app.name}] Failure in app startup: An error occurred while loading items or questions or cache.")
			app.stop()
	
	app.ctx.nfc_counts = sqlite3.connect('data/nfc_counts.db')
	
	app.ctx.login_codes = {}
	
	app.ctx.tpl = Environment(loader=FileSystemLoader("tpl"), autoescape=True)
	app.ctx.tpl.globals.update(time=time)
	app.ctx.tpl.globals.update(PROPIC_DEADLINE=PROPIC_DEADLINE)
	app.ctx.tpl.globals.update(LOCALES=LOCALES)
	app.ctx.tpl.globals.update(ITEMS_ID_MAP=ITEMS_ID_MAP)
	app.ctx.tpl.globals.update(ITEM_VARIATIONS_MAP=ITEM_VARIATIONS_MAP)
	app.ctx.tpl.globals.update(ROOM_TYPE_NAMES=ROOM_TYPE_NAMES)
	app.ctx.tpl.globals.update(PROPIC_MIN_SIZE=PROPIC_MIN_SIZE)
	app.ctx.tpl.globals.update(PROPIC_MAX_SIZE=PROPIC_MAX_SIZE)
	app.ctx.tpl.globals.update(PROPIC_MAX_FILE_SIZE=sizeof_fmt(PROPIC_MAX_FILE_SIZE))
	app.ctx.tpl.globals.update(int=int)
	app.ctx.tpl.globals.update(len=len)

@app.route("/manage/barcode/<code>")
async def gen_barcode(request, code):
	aa = AztecCode(code).image(module_size=8, border=2)
	img = BytesIO()
	aa.save(img, format='PNG')

	return raw(img.getvalue(), content_type="image/png")

@app.route(f"/{ORGANIZER}/{EVENT_NAME}/order/<code>/<secret>/open/<secret2>")
async def redirect_explore(request, code, secret, order: Order, secret2=None):

	r = redirect(app.url_for("welcome"))
	if order and order.code != code: order = None

	if not order:
		res = await pretixClient.get(f"orders/{code}/", expectedStatusCodes=None)
		
		if res.status_code != 200:
			raise exceptions.NotFound("This order code does not exist. Check that your order wasn't deleted, or the link is correct.")
		
		res = res.json()
		if secret != res['secret']:
			raise exceptions.Forbidden("The secret part of the url is not correct. Check your E-Mail for the correct link, or contact support!")
		r.cookies['foxo_code'] = code
		r.cookies['foxo_secret'] = secret
	return r

@app.route("/manage/privacy")
async def privacy(request):
	tpl = app.ctx.tpl.get_template('privacy.html')
	return html(tpl.render())

@app.route("/manage/welcome")
async def welcome(request, order: Order, quota: Quotas):

	if not order:
		raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")
	
	if order.ans("propic_file") is None:
		await resetDefaultPropic(request, order, False)
	if order.ans("propic_fursuiter_file") is None:
		await resetDefaultPropic(request, order, True)

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
	return html(tpl.render(order=order, quota=quota, room_members=room_members, pending_roommates=pending_roommates, ROOM_ERROR_MESSAGES=ROOM_ERROR_TYPES))


@app.route("/manage/download_ticket")
async def download_ticket(request, order: Order):

	if not order:
		raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")
		
	if not order.status != 'confirmed':
		raise exceptions.Forbidden("You are not allowed to download this ticket.")
		
	res = await pretixClient.get(f"orders/{order.code}/download/pdf/", expectedStatusCodes=[200, 404, 409, 403])
	
	if res.status_code == 409 or res.status_code == 404:
		raise exceptions.SanicException("Your ticket is still being generated. Please try again later!", status_code=res.status_code)
	elif res.status_code == 403:
		raise exceptions.SanicException("You can download your ticket only after the order has been confirmed and paid. Try later!", status_code=400)

	return raw(res.content, content_type='application/pdf')

@app.route("/manage/admin")
async def admin(request, order: Order):
	await request.app.ctx.om.update_cache()
	if not order:
		raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")
	if EXTRA_PRINTS:
		logger.info(f"Checking admin credentials of {order.code} with secret {order.secret}")
	if not order.isAdmin(): raise exceptions.Forbidden("Birichino :)")
	tpl = app.ctx.tpl.get_template('admin.html')
	return html(tpl.render(order=order))
	
@app.route("/manage/logout")
async def logout(request):
	orgCode = request.cookies.get("foxo_code_ORG")
	orgSecret = request.cookies.get("foxo_secret_ORG")
	if orgCode != None and orgSecret != None:
		r = redirect(f'/manage/welcome')
		r.cookies['foxo_code'] = orgCode
		r.cookies['foxo_secret'] = orgSecret
		r.delete_cookie("foxo_code_ORG")
		r.delete_cookie("foxo_secret_ORG")
		return r

	raise exceptions.Forbidden("You have been logged out.")

@app.signal("server.shutdown.before")
async def sigintHandler(app, loop):
	killSmptClient()

@app.get(METRICS_PATH)
async def metrics(request):
	return text(getMetricsText() + "\n" + getRoomCountersText(request))

@app.on_request
async def countReqs(request : Request):
	global METRICS_REQ_NO
	if(request.path != METRICS_PATH):
		incReqNo()

if __name__ == "__main__":
	# Wait for pretix in server reboot
	# Using a docker configuration, pretix may be unable to talk with postgres if postgres' service started before it. 
	# To fix this issue I added a After=pretix.service to the [Unit] section of /lib/systemd/system/postgresql@.service
	# to let it start in the correct order. The following piece of code makes sure that pretix is running and can talk to 
	# postgres before actually starting the reserved area, since this operation requires a cache-fill in startup
	print("Waiting for pretix to be up and running", file=sys.stderr)
	while not SKIP_HEALTHCHECK:
		print("Trying connecting to pretix...", file=sys.stderr)
		try:
			incPretixRead()
			res = requests.get(base_url_event, headers=headers)
			res = res.json()
			if(res['slug'] == EVENT_NAME):
				print("Healtchecking...", file=sys.stderr)
				incPretixRead()
				res = requests.get(join(domain, "healthcheck"), headers=headers)
				if(res.status_code == 200):
					break
		except:
			pass
		sleep(5)
	print("Connected to pretix!", file=sys.stderr)

	app.run(host="127.0.0.1", port=8188, dev=DEV_MODE, access_log=ACCESS_LOG)
