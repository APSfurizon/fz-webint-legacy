API_TOKEN = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
ORGANIZER = 'furizon'
EVENT_NAME = 'overlord'
HOSTNAME = 'reg.furizon.net'

headers = {'Host': HOSTNAME, 'Authorization': f'Token {API_TOKEN}'}
base_url = "http://urlllllllllllllllllllll/api/v1/"
base_url_event = f"{base_url}organizers/{ORGANIZER}/events/{EVENT_NAME}/"

PROPIC_DEADLINE = 9999999999
FILL_CACHE = True
CACHE_EXPIRE_TIME = 60 * 60 * 4

DEV_MODE = True

ITEM_IDS = {
	'ticket': [126, 127, 155],
	'membership_card': [128,],
	'sponsorship': [55, 56], # first one = normal, second = super
	'early_arrival': [133],
	'late_departure': [134],
	'room': 135,
	'bed_in_room': 153,
	'daily': 162,
	'daily_addons': [163, 164, 165, 166] #This should be in date order. If there are holes in the daily-span, insert an unexisting id
}

# Create a bunch of "room" items which will get added to the order once somebody gets a room.
# Map variationId -> numberOfPeopleInRoom
ROOM_MAP = {
	# SACRO CUORE
	83: 1,
	67: 2,
	68: 3,
	69: 4,
	70: 5,

	# OVERFLOW 1
	75: 2
}

ROOM_TYPE_NAMES = {
	83: "Park Hotel Sacro Cuore (main hotel) - Single",
	67: "Park Hotel Sacro Cuore (main hotel) - Double",
	68: "Park Hotel Sacro Cuore (main hotel) - Triple",
	69: "Park Hotel Sacro Cuore (main hotel) - Quadruple",
	70: "Park Hotel Sacro Cuore (main hotel) - Quintuple",

	# OVERFLOW 1
	75: "Hotel San Valier (overflow hotel) - Double"
}

# This is used for feedback sending inside of the app. Feedbacks will be sent to the specified chat using the bot api id.
TG_BOT_API = '123456789:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
TG_CHAT_ID = -1234567

# These order codes have additional functions.
ADMINS = ['XXXXX', 'YYYYY']

SMTP_HOST = 'host'
SMTP_USER = 'user'
SMTP_PASSWORD = 'pw'
