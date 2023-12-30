from os.path import join
from config import *
import httpx

QUESTION_TYPES = { #https://docs.pretix.eu/en/latest/api/resources/questions.html
	"number": "N",
	"one_line_string": "S",
	"multi_line_string": "T",
	"boolean": "B",
	"choice_from_list": "C",
	"multiple_choice_from_list": "M",
	"file_upload": "F",
	"date": "D",
	"time": "H",
	"date_time": "W",
	"country_code": "CC",
	"telephone_number": "TEL"
}
TYPE_OF_QUESTIONS = {} # maps questionId -> type


async def loadQuestions():
	global TYPE_OF_QUESTIONS
	TYPE_OF_QUESTIONS.clear()
	async with httpx.AsyncClient() as client:
		p = 0
		while 1:
			p += 1
			res = await client.get(join(base_url_event, f"questions/?page={p}"), headers=headers)

			if res.status_code == 404: break

			data = res.json()
			for q in data['results']:
				TYPE_OF_QUESTIONS[q['id']] = q['type']