from sanic.log import logger, logging
from logging import LogRecord
from config import *

METRICS_REQ_NO = 0
METRICS_ERR_NO = 0 # Errors served to the clients
METRICS_PRETIX_READ = 0
METRICS_PRETIX_WRITE = 0
METRICS_PRETIX_ERRORS = 0 # Errors requesting pretix's backend

def incPretixRead():
	global METRICS_PRETIX_READ
	METRICS_PRETIX_READ += 1

def incPretixWrite():
	global METRICS_PRETIX_WRITE
	METRICS_PRETIX_WRITE += 1

def incPretixErrors():
	global METRICS_PRETIX_ERRORS
	METRICS_PRETIX_ERRORS += 1

def incReqNo():
	global METRICS_REQ_NO
	METRICS_REQ_NO += 1

def incErrorNo(): # Errors served to the clients
	global METRICS_ERR_NO
	METRICS_ERR_NO += 1


def getMetricsText():
	global METRICS_REQ_NO
	global METRICS_ERR_NO
	global METRICS_PRETIX_READ
	global METRICS_PRETIX_WRITE
	global METRICS_PRETIX_ERRORS
	out = []

	out.append(f'sanic_request_count{{}} {METRICS_REQ_NO}')
	out.append(f'sanic_error_count{{}} {METRICS_ERR_NO}')
	out.append(f'webint_pretix_read_count{{}} {METRICS_PRETIX_READ}')
	out.append(f'webint_pretix_write_count{{}} {METRICS_PRETIX_WRITE}')
	out.append(f'webint_pretix_error_count{{}} {METRICS_PRETIX_ERRORS}')

	return "\n".join(out)

def getRoomCountersText(request):
	out = []
	try :
		daily = 0
		counters = {}
		counters_early = {}
		counters_late = {}
		for id in ROOM_TYPE_NAMES.keys():
			counters[id] = 0
			counters_early[id] = 0
			counters_late[id] = 0

		for order in request.app.ctx.om.cache.values():
			if(order.daily):
				daily += 1
			else:
				counters[order.bed_in_room] += 1
				if(order.has_early):
					counters_early[order.bed_in_room] += 1
				if(order.has_late):
					counters_late[order.bed_in_room] += 1

		for id, count in counters.items():
			out.append(f'webint_order_room_counter{{days="normal", label="{ROOM_TYPE_NAMES[id]}"}} {count}')
		for id, count in counters_early.items():
			out.append(f'webint_order_room_counter{{days="early", label="{ROOM_TYPE_NAMES[id]}"}} {count}')
		for id, count in counters_late.items():
			out.append(f'webint_order_room_counter{{days="late", label="{ROOM_TYPE_NAMES[id]}"}} {count}')
		out.append(f'webint_order_room_counter{{label="Daily"}} {daily}')

	except Exception as e:
		print(e)
		logger.warning("Error in loading metrics rooms")
	return "\n".join(out)

class MetricsFilter(logging.Filter):
	def filter(self, record : LogRecord):
		return not (record.request.endswith("/manage/metrics") and record.status == 200)