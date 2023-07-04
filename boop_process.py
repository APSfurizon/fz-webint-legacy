from datetime import datetime
from random import randint
from hashlib import md5
from base64 import b16encode

fibonacci = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
current_date = datetime.today()

async def boop_process(orders, db):
	print(f'Processing {len(orders)} orders')
	db.execute('DELETE FROM player')
	
	for o in orders:
	
		tags = []
		code = o.code
		tag_id = o.nfc_id or b16encode(md5(code.encode()).digest()).decode()[:14]
		birthday = o.birth_date
		badge_id = o.badge_id or randint(0,200)
		room = o.actual_room or randint(100,400)
		country = o.country
		name = o.first_name.lower().strip()

		birth_date = datetime.strptime(birthday, "%Y-%m-%d").date()
		
		age = current_date.year - birth_date.year
		if (current_date.month, current_date.day) < (birth_date.month, birth_date.day):
			age -= 1
		
		# Check if the birthday is today
		if (current_date.month, current_date.day) == (birth_date.month, birth_date.day):
			tags.append('birthday')

		# Check if the badge is a fib number
		if badge_id in fibonacci:
			tags.append('fibonacci')
				
		db.execute('INSERT INTO player(tag_id, code, tags, birthday, badge_id, age, name, room, country) VALUES (?,?,?,?,?,?,?,?,?)',
			(tag_id, code, ','.join(tags), birthday, badge_id, age, name, room, country)
		)
	
	db.commit()
