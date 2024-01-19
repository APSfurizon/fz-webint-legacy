from config import *
from PIL import Image, ImageDraw, ImageFont
from sanic import Blueprint, exceptions
import textwrap

jobs = []

def draw_profile (source, member, position, font, size=(170, 170), border_width=5):
	idraw = ImageDraw.Draw(source)
	source_size = source.size
	main_fill = (187, 198, 206)
	propic_x = position[0]
	propic_y = (source_size[1] // 2) - (size[1] // 2)
	border_loc = (propic_x, propic_y, propic_x + size[0] + border_width * 2, propic_y + size[1] + border_width *2)
	profile_location = (propic_x + border_width, propic_y + border_width)
	propic_name_y = propic_y + size[1] + border_width + 20
	border_color = SPONSORSHIP_COLOR_MAP[member['sponsorship']] if member['sponsorship'] in SPONSORSHIP_COLOR_MAP.keys() else (84, 110, 122)
	# Draw border
	idraw.rounded_rectangle(border_loc, border_width, border_color)
	# Draw profile picture
	with Image.open(f'res/propic/{member['propic'] or 'default.png'}') as to_add:
		source.paste(to_add.resize (size), profile_location)
	name_len = idraw.textlength(str(member['name']), font)
	calc_size = 0
	if name_len > size[0]:
		calc_size = size[0] * 20 / name_len if name_len > size[0] else 20
		font = ImageFont.truetype(font.path, calc_size)
		name_len = idraw.textlength(str(member['name']), font)
	name_loc = (position[0] + ((size[0] / 2) - name_len / 2), propic_name_y + (calc_size/2))
	name_color = SPONSORSHIP_COLOR_MAP[member['sponsorship']] if member['sponsorship'] in SPONSORSHIP_COLOR_MAP.keys() else main_fill
	idraw.text(name_loc, str(member['name']), font=font, fill=name_color)

async def generate_room_preview(request, code, room_data):
	font_path = f'res/font/NotoSans-Bold.ttf'
	main_fill = (187, 198, 206)
	propic_size = (170, 170)
	logo_size = (200, 43)
	border_width = 5
	propic_gap = 50
	propic_width = propic_size[0] + (border_width * 2)
	propic_total_width = propic_width + propic_gap
	jobs.append(code)
	try:
		room_data = await get_room(request, code) if not room_data else room_data
		if not room_data: return
		width = max([(propic_width + propic_gap) * int(room_data['capacity']) + propic_gap, 670])
		height = int(width * 0.525)
		font = ImageFont.truetype(font_path, 20)

		# Recalculate gap
		propic_gap = (width - (propic_width * int(room_data['capacity']))) // (int(room_data['capacity']) + 1)
		propic_total_width = propic_width + propic_gap

		# Define output image
		with Image.new('RGB', (width, height), (17, 25, 31)) as source:
			# Draw logo
			with (Image.open('res/furizon.png') as logo, logo.resize(logo_size).convert('RGBA') as resized_logo):
				source.paste(resized_logo, ((source.size[0] // 2) - (logo_size[0] // 2), 10), resized_logo)
			i_draw = ImageDraw.Draw(source)
			# Draw room's name
			room_name_len = i_draw.textlength(room_data['name'], font)
			i_draw.text((((width / 2) - room_name_len / 2), 55), room_data['name'], font=font, fill=main_fill)
			# Draw members
			for m in range (room_data['capacity']):
				member = room_data['members'][m] if m < len(room_data['members']) else { 'name': 'Empty', 'propic': '../new.png', 'sponsorship': None }
				font = ImageFont.truetype(font_path, 20)
				draw_profile(source, member, (propic_gap + (propic_total_width * m), 63), font, propic_size, border_width)
			source.save(f'res/rooms/{code}.jpg', 'JPEG', quality=60)
	except Exception as err:
		if EXTRA_PRINTS: print(err)
	finally:
		# Remove fault job
		if len(jobs) > 0: jobs.pop()
	if not room_data:
		raise exceptions.SanicException("There's no room with that code.", status_code=404)
	
async def get_room (request, code):
	order_data = await request.app.ctx.om.get_order(code=code)
	if not order_data or not order_data.room_owner: return None
	members_map = [{'name': order_data.name, 'propic': order_data.propic, 'sponsorship': order_data.sponsorship}]
	for member_code in order_data.room_members:
		if member_code == order_data.code: continue
		member_order = await request.app.ctx.om.get_order(code=member_code)
		if not member_order: continue
		members_map.append ({'name': member_order.name, 'propic': member_order.propic, 'sponsorship': member_order.sponsorship})
	return {'name': order_data.room_name, 
		 	'confirmed': order_data.room_confirmed,
			'capacity': order_data.room_person_no,
			'free_spots': order_data.room_person_no - len(members_map),
			'members': members_map}