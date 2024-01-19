ROOM_ERROR_TYPES = {
    'room_id_mismatch': "There's a member in your room that is actually in another room, too. Please contact us as soon as possible in order to fix this issue.",
    'unpaid': "Somebody in your room has not paid for their reservation, yet.",
    'type_mismatch': "A member in your room has a ticket for a different type of room capacity. This happens when users swap their room types with others, without abandoning the room.",
    'daily': "Some member in your room has a Daily ticket. These tickets do not include a hotel reservation.",
    'capacity_mismatch': "The number of people in your room mismatches your type of ticket."
}

ROOM_UNCONFIRM_TITLE = "Your room got unconfirmed"
ROOM_UNCONFIRM_TEXT = {
    'html': "Hello <b>{0}</b><br>We had to unconfirm your room '{1}' due to the following problem/s:<br>{2}<br>Please contact your room's owner or contact our support for further informations at <a href=\"https://furizon.net/contact/\"> https://furizon.net/contact/</a>.<br>Thank you",
    'plain': "Hello {0}\nWe had to unconfirm your room '{1}' due to the following problem/s:\n{2}\nPlease contact your room's owner or contact our support for further informations at https://furizon.net/contact/.\nThank you"
}