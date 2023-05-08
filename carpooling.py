from sanic.response import html, redirect, text
from sanic import Blueprint, exceptions
from random import choice
from ext import *
from config import headers
import json

bp = Blueprint("carpooling", url_prefix="/manage/carpooling")

@bp.get("/")
async def carpooling_list(request, order: Order, error=None):
	if not order: raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")
	
	orders = [value for value in request.app.ctx.om.cache.values() if value.status not in ['c', 'e'] and value.carpooling_message]
	print(orders)

	tpl = request.app.ctx.tpl.get_template('carpooling.html')
	
	return html(tpl.render(orders=orders, order=order, error=error))
	
@bp.post("/")
async def carpooling_update(request, order: Order):
	if not order: raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")

	wants_carpool = request.form.get("wants_carpool")
	error = None
	if wants_carpool == 'on':
		payload = {}
		for field in ['from_location', 'offer_or_need', 'day_departure', 'message']:
			val = request.form.get(field)
			if not val:
				error = f"One of the forms contains invalid values. ({field})"
			elif len(val) > 64 and field != 'message':
				error = "One of the forms contains too long values."
			elif val not in ['offer', 'need'] and field == 'offer_or_need':
				error = "Offer or need form is not valid!"
			elif len(val) > 1000 and field == 'message':
				error = "The message cannot be longer than 1000 characters!"
			elif val.count("\n") > 6:
				error = "Please do not use more than 6 line breaks in the message!"
			else:
				payload[field] = val

		if not error:
			order.carpooling_message = payload
			await order.edit_answer('carpooling_message', json.dumps(payload))

	else:
		order.carpooling_message = {}
		await order.edit_answer('carpooling_message', '{}')

	await order.send_answers()
	
	return await carpooling_list(request, order=order, error=error)
