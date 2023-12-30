from sanic.response import html, redirect
from sanic import Blueprint, exceptions
from ext import *
from config import PROPIC_DEADLINE
from PIL import Image
from io import BytesIO
from hashlib import sha224
from time import time

bp = Blueprint("propic", url_prefix="/manage/propic")

async def resetDefaultPropic(request, order: Order, isFursuiter, sendAnswer=True):
	s = "_fursuiter" if isFursuiter else ""
	print("Resetting default propic")
	with open("res/propic/default.png", "rb") as f:
		data = f.read()
	await order.edit_answer_fileUpload(f'propic{s}_file', f'propic{s}_file_{order.code}_default.png', 'image/png', data)
	if(sendAnswer):
		await order.send_answers()

@bp.post("/upload")
async def upload_propic(request, order: Order):
	if not order: raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")
	
	if order.propic_locked:
		raise exceptions.BadRequest("You have been limited from further editing the propic.")
	
	if request.form.get('submit') != 'Upload' and time() > PROPIC_DEADLINE:
		raise exceptions.BadRequest("The deadline has passed. You cannot modify the badges at this moment.")
		
	if request.form.get('submit') == 'Delete main image':
			await order.edit_answer('propic', None)	
			await resetDefaultPropic(request, order, False, sendAnswer=False)
	elif request.form.get('submit') == 'Delete fursuit image':
			await order.edit_answer('propic_fursuiter', None)
			await resetDefaultPropic(request, order, True, sendAnswer=False)
	else:
		for fn, body in request.files.items():
			if fn not in ['propic', 'propic_fursuiter']:
				continue			

			if not body[0].body: continue
			
			h = sha224(body[0].body).hexdigest()[:32]
			
			try:
				img = Image.open(BytesIO(body[0].body))
				
				with open(f"res/propic/{fn}_{order.code}_original", "wb") as f:
					f.write(body[0].body)
							
				width, height = img.size
				aspect_ratio = width/height
				if aspect_ratio > 1:
					crop_amount = (width - height) / 2
					img = img.crop((crop_amount, 0, width - crop_amount, height))
				elif aspect_ratio < 1:
					crop_amount = (height - width) / 2
					img = img.crop((0, crop_amount, width, height - crop_amount))
					
				img = img.convert('RGB')
				img.thumbnail((512,512))
				imgBytes = BytesIO()
				img.save(imgBytes, format='jpeg')
				imgBytes = imgBytes.getvalue()
				
				with open(f"res/propic/{fn}_{order.code}_{h}.jpg", "wb") as f:
					f.write(imgBytes)

				await order.edit_answer_fileUpload(f'{fn}_file', f'{fn}_file_{order.code}_{h}.jpg', 'image/jpeg', imgBytes)
			except Exception:
				import traceback
				print(traceback.format_exc())
				raise exceptions.BadRequest("The image you uploaded is not valid.")
			else:
				await order.edit_answer(fn, f"{fn}_{order.code}_{h}.jpg")
			
	await order.send_answers()
	return redirect("/manage/welcome#badge")
