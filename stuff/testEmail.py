import smtplib
import ssl

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from secrets import *

SMTP_HOST = 'smtp.office365.com'
SMTP_USER = 'webservice@furizon.net'
SMTP_PORT = 587

plain_body = "Test aaaa"

plain_text = MIMEText(plain_body, "plain")
message = MIMEMultipart("alternative")
message.attach(plain_text)
message['Subject'] = '[Furizon] This is a test!'
message['From'] = 'Furizon <webservice@furizon.net>'
message['To'] = f"Luca Sorace <strdjn@gmail.com>"

print("Start")
context = ssl.create_default_context()
print("Context created")
with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as sender:
	print("Created sender obj")
	sender.starttls(context=context)
	print("Tls started")
	sender.login(SMTP_USER, SMTP_PASSWORD)
	print("Logged in")
	print(sender.sendmail(message['From'], message['to'], message.as_string()))
	print("Mail sent")