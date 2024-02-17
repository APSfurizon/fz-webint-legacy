from sanic.log import logger, logging
from logging import LogRecord
from config import *

METRICS_REQ_NO = 0
METRICS_PRETIX_READ = 0
METRICS_PRETIX_WRITE = 0

def incPretixRead():
	global METRICS_PRETIX_READ
	METRICS_PRETIX_READ += 1

def incPretixWrite():
	global METRICS_PRETIX_WRITE
	METRICS_PRETIX_WRITE += 1

def incReqNo():
	global METRICS_REQ_NO
	METRICS_REQ_NO += 1

def getMetricsText():
	global METRICS_REQ_NO
	global METRICS_PRETIX_READ
	global METRICS_PRETIX_WRITE
	out = []

	out.append(f'sanic_request_count{{}} {METRICS_REQ_NO}')
	out.append(f'webint_pretix_read_count{{}} {METRICS_PRETIX_READ}')
	out.append(f'webint_pretix_write_count{{}} {METRICS_PRETIX_WRITE}')

	return "\n".join(out)

def getRoomCountersText(request):
	out = []
	try :
		daily = 0
		counters = {}
		for id in ROOM_TYPE_NAMES.keys():
			counters[id] = 0

		for order in request.app.ctx.om.cache.values():
			if(order.daily):
				daily += 1
			else:
				counters[order.bed_in_room] += 1

		for id, count in counters.items():
			out.append(f'webint_order_room_counter{{label="{ROOM_TYPE_NAMES[id]}"}} {count}')
		out.append(f'webint_order_room_counter{{label="Daily"}} {daily}')

	except Exception as e:
		print(e)
		logger.warning("Error in loading metrics rooms")
	return "\n".join(out)

class MetricsFilter(logging.Filter):
	def filter(self, record : LogRecord):
		return not (record.request.endswith("/manage/metrics") and record.status == 200)