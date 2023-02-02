from sanic.response import text
from sanic import Blueprint, exceptions
from ext import *
from config import headers

bp = Blueprint("export", url_prefix="/manage/export")

@bp.route("/export.csv")
async def export_csv(request, order: Order):
	if not order: raise exceptions.Forbidden("You have been logged out. Please access the link in your E-Mail to login again!")
	if order.code != 'HWUC9': raise exceptions.Forbidden("Birichino :)")

	page = 0
	orders = {}

	ret = 'code;nome;cognome;nick;nazione;tessera;artista;fursuiter;sponsorship;early;late;shirt;roomsize;roommembers;payment;price\n'

	while 1:
		page += 1
		
		r = httpx.get(f'https://reg.furizon.net/api/v1/organizers/furizon/events/beyond/orders/?page={page}', headers=headers)
		if r.status_code == 404: break
		
		for r in r.json()['results']:
		
			o = Order(r)
			if o.status not in ['pending', 'paid']: continue
			orders[o.code] = o

			ret += (';'.join(map(lambda x: str(x),
			[
				o.code,
				o.first_name,
				o.last_name,
				o.name,
				o.country,
				o.has_card or '',
				o.is_artist or '',
				o.is_fursuiter or '',
				o.sponsorship or '',
				o.has_early or '',
				o.has_late or '',
				o.shirt_size,
				len(o.room_members),
				','.join(o.room_members),
				o.payment_provider,
				o.total-o.fees
			]))) + "\n"

	return text(ret)
