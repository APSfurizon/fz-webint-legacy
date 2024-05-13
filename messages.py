ROOM_ERROR_TYPES = {
	'room_id_mismatch': "There's a member in your room that is actually in another room, too. Please contact us as soon as possible in order to fix this issue.",
	'unpaid': "Somebody in your room has not paid for their reservation, yet.",
	'type_mismatch': "A member in your room has a ticket for a different type of room capacity. This happens when users swap their room types with others, without abandoning the room.",
	'daily': "Some member in your room has a Daily ticket. These tickets do not include a hotel reservation.",
	'capacity_mismatch': "The number of people in your room mismatches your type of ticket.",
	'canceled': "Someone in your room canceled his booking and it was removed from your room."
}

EMAILS_TEXT = {
	"ROOM_UNCONFIRM_TITLE": "Your room got unconfirmed",
	"ROOM_UNCONFIRM_TEXT": {
		'html': "Hello <b>{0}</b><br>We had to <b>unconfirm or change</b> your room <i>'{1}'</i> due to the following issues:<br></p>{2}<br><p>Please contact your room's owner or contact our support for further informations at <a href=\"https://furizon.net/contact/\"> https://furizon.net/contact/</a>.<br>Thank you.<br><br><a class=\"link\" style=\"background-color: #1095c1; color: #fff;\" href=\"https://reg.furizon.net/manage/welcome\">Manage booking</a>",

		'plain': "Hello {0}\nWe had to unconfirm or change your room '{1}' due to the following issues:\n{2}\nPlease contact your room's owner or contact our support for further informations at https://furizon.net/contact/.\nThank you\n\nTo manage your booking: https://reg.furizon.net/manage/welcome"
	},
	

	"MISSING_PROPIC_TITLE": "You haven't uploaded your badges yet!",
	"MISSING_PROPIC_TEXT": {
		'html': "Hello <b>{0}</b><br>We noticed you still have to <b>upload {1}</b>!<br>Please enter your booking page at <a href=\"https://reg.furizon.net/manage/welcome\"> https://reg.furizon.net/manage/welcome</a> and <b>upload them</b> under the <i>\"Badge Customization\"</i> section.<br>Thank you.<br><br><a class=\"link\" style=\"background-color: #1095c1; color: #fff;\" href=\"https://reg.furizon.net/manage/welcome\">Manage booking</a>",

        'plain': "Hello {0}\nWe noticed you still have to upload {1}!\nPlease enter your booking page at https://reg.furizon.net/manage/welcome and upload them under the \"Badge Customization\" section.\nThank you."
    },
}


NOSECOUNT = {
	'filters': {
		'capacity': "Here are some furs that share your room type and don't have a confirmed room."
	}
}

LOCALES = {
	'shuttle_link': {
		'en': 'Book now',
		'it': 'Prenota ora'
	},
	'shuttle_link_url': {
		'en': 'https://visitfiemme.regiondo.com/furizon?_ga=2.129644046.307369854.1705325023-235291123.1705325023',
		'it': 'https://experience.visitfiemme.it/furizon'
	}
}