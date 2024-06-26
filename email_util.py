from sanic import Sanic
from sanic.log import logger
import ssl
from ssl import SSLContext
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from messages import ROOM_ERROR_TYPES
import smtplib
from messages import *
from config import *
from jinja2 import Environment, FileSystemLoader
from threading import Timer, Lock

def killSmptClient():
	global sslLock
	global sslTimer
	global smptSender
	logger.info(f"[SMPT] killSmptClient: Lock status: {sslLock.locked()}")
	sslTimer.cancel()
	sslLock.acquire()
	exp = None
	if(smptSender is not None):
		logger.debug('[SMPT] Closing smpt client')
		try:
			smptSender.quit() # it calls close() inside
		except Exception as e:
			exp = e
		smptSender = None
	sslLock.release()
	if(exp != None):
		raise exp

async def openSmptClient():
	global sslLock
	global sslTimer
	global sslContext
	global smptSender
	logger.info(f"[SMPT] openSmptClient: Lock status: {sslLock.locked()}")
	sslTimer.cancel()
	sslLock.acquire()
	exp = None
	try:
		if(smptSender is None):
			logger.debug('[SMPT] Opening smpt client')
			client : smtplib.SMTP = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
			client.starttls(context=sslContext)
			client.login(SMTP_USER, SMTP_PASSWORD)
			smptSender = client
	except Exception as e:
		exp = e
	sslLock.release()
	sslTimer = createTimer()
	sslTimer.start()
	if(exp != None):
		raise exp

def createTimer():
	return Timer(SMPT_CLIENT_CLOSE_TIMEOUT, killSmptClient)
sslLock : Lock = Lock()
sslTimer : Timer = createTimer()
sslContext : SSLContext = ssl.create_default_context()
smptSender : smtplib.SMTP = None

async def sendEmail(message : MIMEMultipart):
	message['From'] = f'{EMAIL_SENDER_NAME} <{EMAIL_SENDER_MAIL}>'
	await openSmptClient()
	logger.debug(f"[SMPT] Sending mail {message['From']} -> {message['to']} '{message['Subject']}'")
	logger.info(f"[SMPT] sendEmail: Lock status: {sslLock.locked()}")
	exp = None
	sslLock.acquire()
	try:
		smptSender.sendmail(message['From'], message['to'], message.as_string())
	except Exception as e:
		exp = e
	sslLock.release()
	if(exp != None):
		raise exp

def render_email_template(title = "", body = ""):
	tpl = Environment(loader=FileSystemLoader("tpl"), autoescape=False).get_template('email/comunication.html')
	return str(tpl.render(title=title, body=body))




async def send_unconfirm_message(room_order, orders):
	memberMessages = []

	issues_plain = ""
	issues_html = "<ul>"

	for err in room_order.room_errors:
		errId = err[1]
		order = err[0]
		orderStr = ""
		if order is not None:
			orderStr = f"{order}: "
		if errId in ROOM_ERROR_TYPES.keys():
			issues_plain += f" • {orderStr}{ROOM_ERROR_TYPES[errId]}\n"
			issues_html += f"<li>{orderStr}{ROOM_ERROR_TYPES[errId]}</li>"
	issues_html += "</ul>"

	for member in orders:
		if(member.status != 'canceled'):
			plain_body = EMAILS_TEXT["ROOM_UNCONFIRM_TEXT"]['plain'].format(member.name, room_order.room_name, issues_plain)
			html_body = render_email_template(EMAILS_TEXT["ROOM_UNCONFIRM_TITLE"], EMAILS_TEXT["ROOM_UNCONFIRM_TEXT"]['html'].format(member.name, room_order.room_name, issues_html))
			plain_text = MIMEText(plain_body, "plain")
			html_text = MIMEText(html_body, "html")
			message = MIMEMultipart("alternative")
			message.attach(plain_text)
			message.attach(html_text)
			message['Subject'] = f'[{EMAIL_SENDER_NAME}] Your room cannot be confirmed'
			message['To'] = f"{member.name} <{member.email}>"
			memberMessages.append(message)

	if len(memberMessages) == 0: return

	for message in memberMessages:
		await sendEmail(message)

async def send_missing_propic_message(order, missingPropic, missingFursuitPropic):
	t = []
	if(missingPropic): t.append("your propic")
	if(missingFursuitPropic): t.append("your fursuit's badge")
	missingText = " and ".join(t)

	plain_body = EMAILS_TEXT["MISSING_PROPIC_TEXT"]['plain'].format(order.name, missingText)
	html_body = render_email_template(EMAILS_TEXT["MISSING_PROPIC_TITLE"], EMAILS_TEXT["MISSING_PROPIC_TEXT"]['html'].format(order.name, missingText))
	plain_text = MIMEText(plain_body, "plain")
	html_text = MIMEText(html_body, "html")
	message = MIMEMultipart("alternative")
	message.attach(plain_text)
	message.attach(html_text)
	message['Subject'] = f"[{EMAIL_SENDER_NAME}] You haven't uploaded your badges yet!"
	message['To'] = f"{order.name} <{order.email}>"

	await sendEmail(message)
	
async def send_app_login_attempt(user, loginCode):
	#TODO: Format a proper email and add it to messages.py
	msg = MIMEText(f"Hello {user.name}!\n\nWe have received a request to login in the app. If you didn't do this, please ignore this email. Somebody is probably playing with you.\n\nYour login code is: {loginCode}\n\nPlease do not tell this to anybody!")
	msg['Subject'] = '[Furizon] Your login code'
	msg['To'] = f"{user.name} <{user.email}>"

	await sendEmail(msg)