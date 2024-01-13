from email.mime.text import MIMEText
from sanic import response, redirect, Blueprint, exceptions
from config import *
from utils import *
from ext import *
import sqlite3
import smtplib
import random
import string
import httpx
import json

bp = Blueprint("admin", url_prefix="/manage/admin")

def credentialsCheck(request, order:Order):
	if not order:
		raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")
	if EXTRA_PRINTS:
		print(f"Checking admin credentials of {order.code} with secret {order.secret}")
	if not order.isAdmin() : raise exceptions.Forbidden("Birichino :)")



@bp.get('/cache/clear')
async def clearCache(request, order:Order):
	credentialsCheck(request, order)
	await request.app.ctx.om.fill_cache()
	return redirect(f'/manage/admin')

@bp.get('/loginas/<code>')
async def loginAs(request, code, order:Order):
	credentialsCheck(request, order)
	dOrder = await getOrderByCode(request, code, throwException=True)
	if(dOrder.isAdmin()):
		raise exceptions.Forbidden("You can't login as another admin!")

	if EXTRA_PRINTS:
		print(f"Swapping login: {order.secret} {order.code} -> {dOrder.secret} {code}")
	r = redirect(f'/manage/welcome')
	r.cookies['foxo_code_ORG'] = order.code
	r.cookies['foxo_secret_ORG'] = order.secret
	r.cookies['foxo_code'] = code
	r.cookies['foxo_secret'] = dOrder.secret
	return r

@bp.get('/room/unconfirm/<code>')
async def unconfirmRoom(request, code, order:Order):
	credentialsCheck(request, order)
	dOrder = await getOrderByCode(request, code, throwException=True)

	if(not dOrder.room_confirmed):
		raise exceptions.BadRequest("Room is not confirmed!")
		
	ppl = getPeopleInRoomByRoomId(request, code)
	for p in ppl:
		await p.edit_answer('room_confirmed', "False")
		await p.send_answers()

	return redirect(f'/manage/nosecount')

@bp.get('/room/delete/<code>')
async def deleteRoom(request, code, order:Order):
	credentialsCheck(request, order)
	dOrder = await getOrderByCode(request, code, throwException=True)

	ppl = getPeopleInRoomByRoomId(request, code)
	for p in ppl:
		await p.edit_answer('room_id', None)
		await p.edit_answer('room_confirmed', "False")
		await p.edit_answer('room_name', None)
		await p.edit_answer('pending_room', None)
		await p.edit_answer('pending_roommates', None)
		await p.edit_answer('room_members', None)
		await p.edit_answer('room_owner', None)
		await p.edit_answer('room_secret', None)
		await p.send_answers()
	
	await dOrder.send_answers()
	return redirect(f'/manage/nosecount')

@bp.post('/room/rename/<code>')
async def renameRoom(request, code, order:Order):
	credentialsCheck(request, order)
	dOrder = await getOrderByCode(request, code, throwException=True)

	name = request.form.get('name')
	if len(name) > 64 or len(name) < 4:
		raise exceptions.BadRequest("Your room name is invalid. Please try another one.")

	await dOrder.edit_answer("room_name", name)
	await dOrder.send_answers()
	return redirect(f'/manage/nosecount')