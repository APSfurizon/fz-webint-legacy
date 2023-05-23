from sanic.response import html, redirect, text
from sanic import Blueprint, exceptions
from random import choice
from ext import *
from config import headers, PROPIC_DEADLINE
from PIL import Image
from os.path import isfile
from os import unlink
from io import BytesIO
from hashlib import sha224
from time import time
from urllib.parse import unquote
import json

bp = Blueprint("karaoke", url_prefix="/manage/karaoke")

@bp.get("/admin")
async def show_songs(request, order: Order):

	if order.code not in ['9YKGJ', 'CMPQG']:
		raise exceptions.Forbidden("Birichino")

	orders = [x for x in request.app.ctx.om.cache.values() if x.karaoke_songs]

	songs = []
	for o in orders:
		if not o.karaoke_songs: continue
		
		for song, data in o.karaoke_songs.items():
			songs.append({'song': song, 'order': o, **data})

	tpl = request.app.ctx.tpl.get_template('karaoke_admin.html')
	return html(tpl.render(songs=songs))

@bp.post("/add")
async def add_song(request, order: Order):
	if not order: raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")

	song = request.form.get('song')
	
	if not song:
		raise exceptions.BadRequest("This song is not valid!")
	
	karaoke_songs = order.karaoke_songs or {}
	if song not in karaoke_songs:
		karaoke_songs[song[:64]] = {'approved': None, 'ts': time(), 'contest': bool(request.form.get('wants_contest'))}

	await order.edit_answer('karaoke_songs', json.dumps(karaoke_songs))
	await order.send_answers()
		
	return redirect("/manage/welcome#karaoke")
	
@bp.get("/delete/<songname>")
async def del_song(request, order: Order, songname):
	
	if not order: raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")

	karaoke_songs = order.karaoke_songs or {}
	songname = unquote(songname)
	
	if not songname in karaoke_songs:
		raise exceptions.BadRequest(f"The song you're trying to delete {songname} does not exist in your list of songs.")
		
	del karaoke_songs[songname]
	await order.edit_answer('karaoke_songs', json.dumps(karaoke_songs))
	await order.send_answers()
	
	return redirect("/manage/welcome#karaoke")
	
