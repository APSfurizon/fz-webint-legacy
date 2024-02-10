from sanic import Sanic
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from messages import ROOM_ERROR_TYPES
import smtplib
from messages import *
from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
from jinja2 import Environment, FileSystemLoader

async def send_unconfirm_message (room_order, orders):
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
		plain_body = ROOM_UNCONFIRM_TEXT['plain'].format(member.name, room_order.room_name, issues_plain)
		html_body = render_email_template(ROOM_UNCONFIRM_TITLE, ROOM_UNCONFIRM_TEXT['html'].format(member.name, room_order.room_name, issues_html))
		plain_text = MIMEText(plain_body, "plain")
		html_text = MIMEText(html_body, "html")
		message = MIMEMultipart("alternative")
		message.attach(plain_text)
		message.attach(html_text)
		message['Subject'] = '[Furizon] Your room cannot be confirmed'
		message['From'] = 'Furizon <no-reply@furizon.net>'
		message['To'] = f"{member.name} <{member.email}>"
		memberMessages.append(message)

	if len(memberMessages) == 0: return

	with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as sender:
		sender.login(SMTP_USER, SMTP_PASSWORD)
		for message in memberMessages:
			sender.sendmail(message['From'], message['to'], message.as_string())

def render_email_template(title = "", body = ""):
	tpl = Environment(loader=FileSystemLoader("tpl"), autoescape=False).get_template('email/comunication.html')
	return str(tpl.render(title=title, body=body))