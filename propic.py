from sanic.response import html, redirect
from sanic import Blueprint, exceptions
from ext import *
from config import PROPIC_DEADLINE
from PIL import Image
from io import BytesIO
from hashlib import sha224
from time import time
import os

bp = Blueprint("propic", url_prefix="/manage/propic")

async def resetDefaultPropic(request, order: Order, isFursuiter, sendAnswer=True):
	s = "_fursuiter" if isFursuiter else ""
	if (EXTRA_PRINTS): 
		print("Resetting {fn} picture for {orderCod}".format(fn="Badge" if not isFursuiter else "fursuit", orderCod = order.code))
	with open("res/propic/default.png", "rb") as f:
		data = f.read()
		f.close()
	
	convertedFilename = order.ans(f'propic{s}')
	if convertedFilename is not None:
		convertedFilename = f"res/propic/{convertedFilename}"
		if os.path.exists(convertedFilename):
			os.remove(convertedFilename) # converted file
	originalFilename = f"res/propic/propic{s}_{order.code}_original"
	if os.path.exists(originalFilename):
		os.remove(originalFilename) # original file
	
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
			await resetDefaultPropic(request, order, False, sendAnswer=False)
			await order.edit_answer('propic', None)	#This MUST come after the reset default propic!
	elif request.form.get('submit') == 'Delete fursuit image':
			await resetDefaultPropic(request, order, True, sendAnswer=False)
			await order.edit_answer('propic_fursuiter', None) #This MUST come after the reset default propic!
	else:
		for fn, body in request.files.items():
			if fn not in ['propic', 'propic_fursuiter']:
				continue			

			if not body[0].body: continue
			
			# Check max file size
			if len(body[0].body) > PROPIC_MAX_FILE_SIZE:
				raise exceptions.BadRequest("File size too large for " + ("Profile picture" if fn == 'propic' else 'Fursuit picture'))
			
			errorDetails = ''
			bodyBytesBuff = None
			imgBytesBuff = None
			img = None
			try:
				bodyBytesBuff = BytesIO(body[0].body)
				img = Image.open(bodyBytesBuff)
				width, height = img.size
				# Checking for min / max size
				if width < PROPIC_MIN_SIZE[0] or height < PROPIC_MIN_SIZE[1]:
					errorDetails = "Image too small [{width}x{width}] for {pfpn}".format(width=width, pfpn=("Profile picture" if fn == 'propic' else 'Fursuit picture'))
					raise exceptions.BadRequest(errorDetails)

				if width > PROPIC_MAX_SIZE[0] or height > PROPIC_MAX_SIZE[1]:
					errorDetails = "Image too big [{width}x{width}] for {pfpn}".format(width=width, pfpn=("Profile picture" if fn == 'propic' else 'Fursuit picture'))
					raise exceptions.BadRequest(errorDetails)

				
				with open(f"res/propic/{fn}_{order.code}_original", "wb") as f:
					f.write(body[0].body)
							
				aspect_ratio = width/height
				if aspect_ratio > 1:
					crop_amount = (width - height) / 2
					img = img.crop((crop_amount, 0, width - crop_amount, height))
				elif aspect_ratio < 1:
					crop_amount = (height - width) / 2
					img = img.crop((0, crop_amount, width, height - crop_amount))
					
				img = img.convert('RGB')
				width, height = img.size

				img.thumbnail((512,512))
				imgBytesBuff = BytesIO()
				img.save(imgBytesBuff, format='jpeg')
				imgBytes = imgBytesBuff.getvalue()
				with open(f"res/propic/{fn}_{order.code}.jpg", "wb") as f:
					f.write(imgBytes)

				await order.edit_answer_fileUpload(f'{fn}_file', f'{fn}_file_{order.code}.jpg', 'image/jpeg', imgBytes)
			except Exception:
				import traceback
				if EXTRA_PRINTS: print(traceback.format_exc())
				raise exceptions.BadRequest(errorDetails if errorDetails else "The image you uploaded is not valid.")
			else:
				await order.edit_answer(fn, f"{fn}_{order.code}.jpg")
			
			if img is not None:
				img.close()
			if bodyBytesBuff is not None:
				bodyBytesBuff.flush()
				bodyBytesBuff.close()
			if imgBytesBuff is not None:
				imgBytesBuff.flush()
				imgBytesBuff.close()
			
	await order.send_answers()
	return redirect("/manage/welcome#badge")
