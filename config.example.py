ORGANIZER = 'furizon'
EVENT_NAME = 'river-side-2023'
API_TOKEN = 'xxxxxxxxxxxxxxxxxxxxxx'
HOSTNAME = 'your-pretix-hostname'

headers = {'Host': HOSTNAME, 'Authorization': f'Token {API_TOKEN}'}
base_url = f"https://{HOSTNAME}/api/v1/organizers/{ORGANIZER}/events/{EVENT_NAME}/"

PROPIC_DEADLINE = 1683575684
FILL_CACHE = True

DEV_MODE = True

ITEM_IDS = {
	'ticket': [90,],
	'membership_card': [91,],
	'sponsorship': [], # first one = normal, second = super
	'early_arrival': [],
	'late_departure': [],
	'room': 98
}

# Create a bunch of "room" items which will get added to the order once somebody gets a room.
ROOM_MAP = {
			1: 16,
			2: 17,
			3: 18,
			4: 19,
			5: 20
}

# This is used for feedback sending inside of the app. Feedbacks will be sent to the specified chat using the bot api id.
TG_BOT_API = '123456789:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
TG_CHAT_ID = -1234567

# These order codes have additional functions.
ADMINS = ['XXXXX', 'YYYYY']

SMTP_HOST = 'your-smtp-host.com'
SMTP_USER = 'username'
SMTP_PASSWORD = 'password'
