API_TOKEN = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
ORGANIZER = 'furizon'
EVENT_NAME = 'overlord'
HOSTNAME = 'reg.furizon.net'

headers = {'Host': HOSTNAME, 'Authorization': f'Token {API_TOKEN}'}
base_url = "http://urlllllllllllllllllllll/api/v1/"
base_url_event = f"{base_url}organizers/{ORGANIZER}/events/{EVENT_NAME}/"

PROPIC_DEADLINE = 9999999999
PROPIC_MAX_FILE_SIZE = 5 * 1024 * 1024 # 5MB
PROPIC_MAX_SIZE = (2048, 2048) # (Width, Height)
PROPIC_MIN_SIZE = (125, 125) # (Width, Height)

FILL_CACHE = True
CACHE_EXPIRE_TIME = 60 * 60 * 4

DEV_MODE = True
ACCESS_LOG = True
EXTRA_PRINTS = True

# Metadata property for item-id mapping
METADATA_NAME = "item_name"
# Metadata property for internal category mapping (not related to pretix's category)
METADATA_CATEGORY = "category_name"

# Maps Products metadata name <--> ID
ITEMS_ID_MAP = {
	'early_bird_ticket': 126,
	'regular_ticket': 127,
	'staff_ticket': 155,
    'daily_ticket': 162,
    'sponsorship_item': 129,
    'early_arrival_admission': 133,
    'late_departure_admission': 134,
    'membership_card_item': 128,
    'bed_in_room': 153,
    'room_type': 135,
    'room_guest': 136,
    'daily_1': 163,
    'daily_2': 164,
    'daily_3': 165,
    'daily_4': 166,
    'daily_5': None
}

# Maps Products' variants metadata name <--> ID
ITEM_VARIATIONS_MAP = {
    'sponsorship_item': {
        'sponsorship_item_normal': 55,
        'sponsorship_item_super': 56
    },
    'bed_in_room': {
        'bed_in_room_main_1': 83,
        'bed_in_room_main_2': 67,
        'bed_in_room_main_3': 68,
        'bed_in_room_main_4': 69,
        'bed_in_room_main_5': 70,
        'bed_in_room_overflow1_2': 75,
    },
    'room_type': {
        'single': 57,
        'double': 58,
        'triple': 59,
        'quadruple': 60,
        'quintuple': 61
    },
    'room_guest': {
        'single': 57,
        'double': 58,
        'triple': 59,
        'quadruple': 60,
        'quintuple': 61
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
	# SACRO CUORE
    'bed_in_room_main_1': 1,
    'bed_in_room_main_2': 2,
    'bed_in_room_main_3': 3,
    'bed_in_room_main_4': 4,
    'bed_in_room_main_5': 5,

    # OVERFLOW 1
    'bed_in_room_overflow1_2': 2,
}

# Autofilled
ROOM_TYPE_NAMES = { }

# This is used for feedback sending inside of the app. Feedbacks will be sent to the specified chat using the bot api id.
TG_BOT_API = '123456789:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
TG_CHAT_ID = -1234567

# These order codes have additional functions.
ADMINS = ['XXXXX', 'YYYYY']

SMTP_HOST = 'host'
SMTP_USER = 'user'
SMTP_PASSWORD = 'pw'
