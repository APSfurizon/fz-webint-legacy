from sanic import response
from sanic import Blueprint, exceptions
from ext import *
from config import *
import sqlite3
import smtplib
from email.mime.text import MIMEText
import random
import string

bp = Blueprint("api", url_prefix="/manage/api")

@bp.route("/members.json")
async def api_members(request):
	
	ret = []
	
	for o in sorted(request.app.ctx.om.cache.values(), key=lambda x: len(x.room_members), reverse=True):
		if o.status in ['c', 'e']: continue
		
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
			'is_checked_in': False
		})
		
	return response.json(ret)
	
@bp.route("/events.json")
async def show_events(request):

	with sqlite3.connect('data/event.db') as db:
		db.row_factory = sqlite3.Row
		events = db.execute('SELECT * FROM event ORDER BY start ASC')
		return response.json([dict(x) for x in events])
		
@bp.route("/achievements.json")
async def show_events(request):

	code = request.args.get("code")

	with sqlite3.connect('data/achievement.db') as db:
		db.row_factory = sqlite3.Row
		events = db.execute('SELECT * FROM achievement ORDER BY ' + ('random() LIMIT 5' if code else 'points'))
		return response.json([{'won_at': '2023-05-05T21:00Z' if code else None, **dict(x), 'about': 'This is instructions on how to win the field.'} for x in events])

@bp.get("/logout")
async def logout(request):
	if not request.token:
		return response.json({'ok': False, 'error': 'You need to provide a token.'}, status=401)
		
	user = await request.app.ctx.om.get_order(code=request.token[:5])
	if not user or user.api_token != request.token[5:]:
		return response.json({'ok': False, 'error': 'The token you have provided is not valid.'}, status=401)
		
	user.edit_answer('api_token', None)
	await user.send_answers()
	
	return response.json({'ok': True, 'message': 'You have been logged out and this token has been destroyed.'})
	print(request.token)

@bp.get("/get_token/<code>/<login_code>")
async def get_token_from_code(request, code, login_code):
	if not code in request.app.ctx.login_codes:
		return response.json({'ok': False, 'error': 'You need to reauthenticate. The code has expired.'}, status=401)
		
	if request.app.ctx.login_codes[code][1] == 0:
		del request.app.ctx.login_codes[code]
		return response.json({'ok': False, 'error': 'Too many tries. Please reauthenticate again.'}, status=401)
		
	if request.app.ctx.login_codes[code][0] != login_code:
		request.app.ctx.login_codes[code][1] -= 1
		return response.json({'ok': False, 'error': 'The login code is incorrect. Try again.'}, status=401)
	
	user = await request.app.ctx.om.get_order(code=code)
	token = ''.join(random.choice(string.ascii_letters) for _ in range(48))
	user.edit_answer('api_token', token)
	await user.send_answers()
	
	return response.json({'ok': True, 'token': code+token})

@bp.route("/get_token/<code>")
async def get_token(request, code):
	user = await request.app.ctx.om.get_order(code=code)
	
	if not user:
		return response.json({'ok': False, 'error': 'The user you have requested does not exist.'}, status=404)

	if user.status != 'paid':
		return response.json({'ok': False, 'error': 'This user is not allowed to login.'}, status=401)

	if not user.email:
		return response.json({'ok': False, 'error': 'This user has not provided their email.'}, status=401)

	request.app.ctx.login_codes[code] = [''.join(random.choice(string.digits) for _ in range(6)), 3]

	try:
		msg = MIMEText(f"Hello {user.name}!\n\nWe have received a request to login in the app. If you didn't do this, please ignore this email. Somebody is probably playing with you.\n\nYour login code is: {request.app.ctx.login_codes[code][0]}\n\nPlease do not tell this to anybody!")
		msg['Subject'] = '[Furizon] Your login code'
		msg['From'] = 'Furizon <no-reply@furizon.net>'
		msg['To'] = f"{user.name} <{user.email}>"

		s = smtplib.SMTP_SSL(SMTP_HOST)
		s.login(SMTP_USER, SMTP_PASSWORD)
		s.sendmail(msg['From'], msg['to'], msg.as_string())
		s.quit()
	except:
		return response.json({'ok': False, 'error': 'There has been an issue sending your e-mail. Please try again later or report to an admin.'}, status=500)
	
	return response.json({'ok': True, 'message': 'A login code has been sent to your email.'})
	
