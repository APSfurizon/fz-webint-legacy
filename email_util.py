from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from messages import ROOM_ERROR_TYPES
import smtplib
from messages import *
from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_ADMIN_PASS

def send_unconfirm_message (room_order, room_errors, orders, title):
    memberMessages = []

    issues_plain = ""
    issues_html = "<ul>"

    for err in room_errors:
        if err in ROOM_ERROR_TYPES.keys():
            issues_plain += f"{ROOM_ERROR_TYPES[err]}"
            issues_html += f"<li>{ROOM_ERROR_TYPES[err]}</li>"
        issues_html += "</ul>"

    for member in orders:
        plain_body = ROOM_UNCONFIRM_TEXT['plain'].format(member.name, room_order.room_name, issues_plain)
        html_body = ROOM_UNCONFIRM_TEXT['html'].format(member.name, room_order.room_name, issues_html)
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

def render_email_template(title = "", body = ""):
    tpl = app.ctx.tpl.get_template('email/comunication.html')
    return str(tpl.render(title=title, body=body))