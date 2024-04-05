from sanic.log import logging
LOG_LEVEL = logging.DEBUG

API_TOKEN = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
ORGANIZER = 'furizon'
EVENT_NAME = 'overlord'
HOSTNAME = 'reg.furizon.net'
SKIP_HEALTHCHECK = False

headers = {'Host': HOSTNAME, 'Authorization': f'Token {API_TOKEN}'}
domain = "http://urlllllllllllllllllllll/"
base_url = "{domain}api/v1/"
base_url_event = f"{base_url}organizers/{ORGANIZER}/events/{EVENT_NAME}/"

PROPIC_DEADLINE = 9999999999
PROPIC_MAX_FILE_SIZE = 5 * 1024 * 1024 # 5MB
PROPIC_MAX_SIZE = (2048, 2048) # (Width, Height)
PROPIC_MIN_SIZE = (125, 125) # (Width, Height)

# This is used for feedback sending inside of the app. Feedbacks will be sent to the specified chat using the bot api id.
TG_BOT_API = '123456789:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
TG_CHAT_ID = -1234567

import httpx
# Number of tries for a request to the pretix's backend
PRETIX_REQUESTS_MAX = 3
PRETIX_REQUESTS_TIMEOUT = httpx.Timeout(15.0, read=30.0, connect=45.0, pool=None) # Timeout for httpx requests in seconds

# These order codes have additional functions.
ADMINS = ['XXXXX', 'YYYYY']
# A list of staff_roles 
ADMINS_PRETIX_ROLE_NAMES = ["Reserved Area admin", "main staff"]

SMTP_HOST = 'host'
SMTP_PORT = 0
SMTP_USER = 'user'
SMTP_PASSWORD = 'pw'
EMAIL_SENDER_NAME = "Fantastic Furcon Wow"
EMAIL_SENDER_MAIL = "no-reply@thisIsAFantasticFurconWowItIsWonderful.cuteFurries.ovh"
SMPT_CLIENT_CLOSE_TIMEOUT = 60 * 15 # 15 minutes

FILL_CACHE = True
CACHE_EXPIRE_TIME = 60 * 60 * 4

DEV_MODE = True
ACCESS_LOG = True
EXTRA_PRINTS = True

UNCONFIRM_ROOMS_ENABLE = True

METRICS_PATH = "/welcome/metrics"

# Additional configured locales.
# If an order has a country that's not listed here,
# Will default to an english preference.
AVAILABLE_LOCALES = ['it',]

# Metadata property for item-id mapping
METADATA_NAME = "item_name"
# Metadata property for internal category mapping (not related to pretix's category)
METADATA_CATEGORY = "category_name"

SPONSORSHIP_COLOR_MAP = {
    'super': (251, 140, 0),
    'normal': (142, 36, 170)
}

# Maps Products metadata name <--> ID
ITEMS_ID_MAP = {
	'early_bird_ticket': None,
	'regular_ticket': None,
	'staff_ticket': None,
    'daily_ticket': None,
	'regular_bundle_sponsor_ticket': None,
    'sponsorship_item': None,
    'early_arrival_admission': None,
    'late_departure_admission': None,
    'membership_card_item': None,
    'bed_in_room': None,
    'room_type': None,
    'room_guest': None,
    'daily_1': None,
    'daily_2': None,
    'daily_3': None,
    'daily_4': None,
    'daily_5': None
}

# Maps Products' variants metadata name <--> ID
ITEM_VARIATIONS_MAP = {
    'sponsorship_item': {
        'sponsorship_item_normal': None,
        'sponsorship_item_super': None
    },
    'bed_in_room': {
		'bed_in_room_no_room': None,
        'bed_in_room_main_1': None,
        'bed_in_room_main_2': None,
        'bed_in_room_main_3': None,
        'bed_in_room_main_4': None,
        'bed_in_room_main_5': None,
        'bed_in_room_overflow1_2': None,
    },
    'room_type': {
        'single': None,
        'double': None,
        'triple': None,
        'quadruple': None,
        'quintuple': None
    },
    'room_guest': {
        'single': None,
        'double': None,
        'triple': None,
        'quadruple': None,
        'quintuple': None
    }
}

ADMINS_PRETIX_ROLE_NAMES = ["Reserved Area admin", "main staff"]

# Links Products' variants' ids with the internal category name
CATEGORIES_LIST_MAP = {
    'tickets': [],
    'memberships': [],
    'sponsorships': [],
    'tshirts': [],
    'extra_days': [],
    'rooms': [],
    'dailys': []
}

# Create a bunch of "room" items which will get added to the order once somebody gets a room.
# Map item_name -> room capacity
ROOM_CAPACITY_MAP = {
	# Default
	'bed_in_room_no_room': 0,

	# SACRO CUORE
    'bed_in_room_main_1': 1,
    'bed_in_room_main_2': 2,
    'bed_in_room_main_3': 3,
    'bed_in_room_main_4': 4,
    'bed_in_room_main_5': 5,

    # OVERFLOW 1
    'bed_in_room_overflow1_2': 2,
}

# Autofilled. Maps roomTypeId -> roomName
ROOM_TYPE_NAMES = { }