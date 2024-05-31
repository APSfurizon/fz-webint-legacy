from sanic import response
from sanic import Blueprint
from ext import *
from config import *
import sqlite3
import smtplib
from email.mime.text import MIMEText
import random
import string
import httpx
import json
import traceback
from sanic.log import logger
from email_util import send_app_login_attempt

bp = Blueprint("api", url_prefix="/manage/api")

@bp.route("/members.json")
async def api_members(request):
	
	ret = []
	
	for o in sorted(request.app.ctx.om.cache.values(), key=lambda x: len(x.room_members), reverse=True):
		if o.status in ['expired', 'canceled']: continue
		
		ret.append({
			'code': o.code,
			'sponsorship': o.sponsorship,
			'is_fursuiter': o.is_fursuiter,
			'name': o.name,
			'has_early': o.has_early,
			'has_late': o.has_late,
			'propic': o.ans('propic'),
			'propic_fursuiter': o.ans('propic_fursuiter'),
			'staff_role': o.ans('staff_role'),
			'country': o.country,
			'room_id': o.room_id,
			'is_checked_in': o.checked_in,
			'points': random.randint(0,50) if random.random() > 0.3 else 0
		})
		
	return response.json(ret)
	
@bp.route("/leaderboard.json")
async def api_leaderboard(request):
	
	ret = []
	
	for o in request.app.ctx.om.cache.values():
		if o.status in ['expired', 'canceled']: continue
		
		ret.append({
			'name': o.name,
			'propic': o.ans('propic'),
			'points': 0,
		})
		
	ret = sorted(ret, key=lambda x: x['points'], reverse=True)
	
	return response.json(ret)

@bp.post("/feedback")
async def send_feedback(request):
	try:
		async with httpx.AsyncClient() as client:
			r = await client.post(f"https://api.telegram.org/bot{TG_BOT_API}/sendMessage",
				json = {'chat_id': TG_CHAT_ID, 'text': str(request.json)}
			)
	except:
		return response.json({'ok': False, 'error': 'There has been an issue sending your feedback.'})
	else:
		return response.json({'ok': True, 'message': 'Your feedback has been sent'})
		
@bp.post("/event_feedback")
async def send_event_feedback(request):
	with open('data/event_feedback.json', 'a') as f:
		f.write(json.dumps(request.json)+"\n")

	return response.json({'ok': True, 'message': 'Your feedback has been sent'})

@bp.route("/events.json")
async def show_events(request):
	with sqlite3.connect('data/event.db') as db:
		db.row_factory = sqlite3.Row
		events = db.execute('SELECT * FROM event ORDER BY start ASC')

		r = response.json([dict(x) for x in events])
		r.headers["Access-Control-Allow-Origin"] = "*"
		
		return r

@bp.get("/logout")
async def logout(request):
	if not request.token:
		return response.json({'ok': False, 'error': 'You need to provide a token.'}, status=401)
		
	user = await request.app.ctx.om.get_order(code=request.token[:5])
	if not user or user.app_token != request.token[5:]:
		return response.json({'ok': False, 'error': 'The token you have provided is not valid.'}, status=401)
		
	await user.edit_answer('app_token', None)
	await user.send_answers()
	
	return response.json({'ok': True, 'message': 'You have been logged out and this token has been destroyed.'})

@bp.get("/test")
async def token_test(request):
	if not request.token:
		return response.json({'ok': False, 'error': 'You need to provide a token.'}, status=401)
		
	user = await request.app.ctx.om.get_order(code=request.token[:5])
	if not user or user.app_token != request.token[5:]:
		return response.json({'ok': False, 'error': 'The token you have provided is not correct.'}, status=401)
	
	return response.json({'ok': True, 'message': 'This token is valid :)'})

@bp.get("/ping")
async def ping(request):
	return response.text("pong")
	
@bp.get("/welcome")
async def welcome_app(request):

	ret = {
		'phone': None,
		'message': 'Reception open now!'
	}
	
	if not request.token:
		return response.json(ret)
		
	o = await request.app.ctx.om.get_order(code=request.token[:5])
	if not o or o.app_token != request.token[5:]:
		return response.json({'ok': False, 'error': 'The token you have provided is not correct.'}, status=401)
	
	return response.json({
		'code': o.code,
		'sponsorship': o.sponsorship,
		'is_fursuiter': o.is_fursuiter,
		'name': o.name,
		'has_early': o.has_early,
		'has_late': o.has_late,
		'propic': o.ans('propic'),
		'propic_fursuiter': o.ans('propic_fursuiter'),
		'staff_role': o.ans('staff_role'),
		'country': o.country,
		'is_checked_in': o.checked_in,
		'points': random.randint(0,50) if random.random() > 0.3 else 0,
		'can_scan_nfc': o.can_scan_nfc,
		'room_id': o.room_id,
		#'mail': o.email,
		'actual_room_id': o.actual_room,
		**ret
	})
	
@bp.get("/scan/<nfc_id>")
async def nfc_scan(request, nfc_id):
	return response.text("Nope")
	if not request.token:
		return response.json({'ok': False, 'error': 'You need to provide a token.'}, status=401)
		
	user = await request.app.ctx.om.get_order(code=request.token[:5])
	if not user or user.app_token != request.token[5:]:
		return response.json({'ok': False, 'error': 'The token you have provided is not correct.'}, status=401)
		
	if not user.can_scan_nfc:
		return response.json({'ok': False, 'error': 'You cannot scan NFC at this time.'}, status=401)
	
	for o in request.app.ctx.om.cache.values():
		if nfc_id in [o.nfc_id, o.code, o.barcode]:
		
			room_owner = request.app.ctx.om.cache[o.room_id]
		
			return response.json({
			'code': o.code,
			'sponsorship': o.sponsorship,
			'is_fursuiter': o.is_fursuiter,
			'name': o.name,
			'has_early': o.has_early,
			'has_late': o.has_late,
			'propic': o.ans('propic'),
			'propic_fursuiter': o.ans('propic_fursuiter'),
			'staff_role': o.ans('staff_role'),
			'country': o.country,
			'is_checked_in': o.checked_in,
			'points': random.randint(0,50) if random.random() > 0.3 else 0,
			'comment': o.comment,
			'actual_room_id': o.actual_room,
			'phone': o.phone,
			'room_id': o.room_id,
			'telegram_username': o.telegram_username,
			'roommates': {x: (await request.app.ctx.om.get_order(code=x, cached=True)).name for x in room_owner.room_members if x != o.code}
		})

	return response.json({'ok': False, 'error': 'This NFC tag is not valid.'})

@bp.get("/get_token/<code>/<login_code>")
async def get_token_from_code(request, code, login_code):
	if not code in request.app.ctx.login_codes:
		if DEV_MODE and EXTRA_PRINTS:
			logger.debug(request.app.ctx.login_codes)
		return response.json({'ok': False, 'error': 'You need to reauthenticate. The code has expired.'}, status=401)
		
	if request.app.ctx.login_codes[code][1] == 0:
		del request.app.ctx.login_codes[code]
		return response.json({'ok': False, 'error': 'Too many tries. Please reauthenticate again.'}, status=401)
		
	if request.app.ctx.login_codes[code][0] != login_code:
		request.app.ctx.login_codes[code][1] -= 1
		return response.json({'ok': False, 'error': 'The login code is incorrect. Try again.'}, status=401)
	
	user = await request.app.ctx.om.get_order(code=code)
	token = ''.join(random.choice(string.ascii_letters) for _ in range(48))
	await user.edit_answer('app_token', token)
	await user.send_answers()
	
	return response.json({'ok': True, 'token': code+token})

@bp.route("/get_token/<code>")
async def get_token(request, code):
	user = await request.app.ctx.om.get_order(code=code)
	
	if not user:
		return response.json({'ok': False, 'error': 'The user you have requested does not exist.'}, status=404)

	if user.status in ['expired', 'canceled']:
		return response.json({'ok': False, 'error': 'This user is not allowed to login because the order has been canceled.'}, status=401)

	if not user.email:
		return response.json({'ok': False, 'error': 'This user has not provided their email.'}, status=401)

	request.app.ctx.login_codes[code] = [''.join(random.choice(string.digits) for _ in range(6)), 3]

	try:
		await send_app_login_attempt(user, request.app.ctx.login_codes[code][0])
	except Exception:
		logger.error(f"[API] [GET_TOKEN] Error while sending email.\n{traceback.format_exc()}")
		return response.json({'ok': False, 'error': 'There has been an issue sending your e-mail. Please try again later or report to an admin.'}, status=500)
	
	return response.json({'ok': True, 'message': 'A login code has been sent to your email.'})
	
