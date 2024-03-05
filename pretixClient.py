import httpx
from utils import *
from config import *
from sanic.log import logger
from metrics import *
import traceback
import asyncio

async def get(url, baseUrl=base_url_event, headers=headers, expectedStatusCodes=[200]) -> httpx.Response:
	async def func(client : httpx.AsyncClient) -> httpx.Request:
		return await client.get(join(baseUrl, url), headers=headers)
	return await doReq(url, func, incPretixRead, expectedStatusCodes, "GETing")

async def post(url, content=None, json=None, baseUrl=base_url_event, headers=headers, expectedStatusCodes=[200]) -> httpx.Response:
	async def func(client : httpx.AsyncClient) -> httpx.Request:
		return await client.post(join(baseUrl, url), headers=headers, content=content, json=json)
	return await doReq(url, func, incPretixWrite, expectedStatusCodes, "POSTing")
	
async def patch(url, json, baseUrl=base_url_event, headers=headers, expectedStatusCodes=[200]) -> httpx.Response:
	async def func(client : httpx.AsyncClient) -> httpx.Request:
		return await client.patch(join(baseUrl, url), headers=headers, json=json)
	return await doReq(url, func, incPretixWrite, expectedStatusCodes, "PATCHing")



async def doReq(url, httpxFunc, metricsFunc, expectedStatusCodes, opLogString) -> httpx.Response:
	res = None
	async with httpx.AsyncClient(timeout=PRETIX_REQUESTS_TIMEOUT) as client:
		requests = 0
		for requests in range(PRETIX_REQUESTS_MAX):
			try:
				metricsFunc()
				res : httpx.Response = await httpxFunc(client)

				if expectedStatusCodes is not None and res.status_code not in expectedStatusCodes:
					incPretixErrors()
					logger.warning(f"[PRETIX] Got an unexpected status code ({res.status_code}) while {opLogString} '{url}'. Allowed status codes: {', '.join(map(str, expectedStatusCodes))}")
					logger.debug(f"Response: '{res.text}'")
					continue
				break
			except Exception as e:
				incPretixErrors()
				logger.warning(f"[PRETIX] An error ({requests}) occurred while {opLogString} '{url}':\n{traceback.format_exc()}")

			requests += 1
		else:
			logger.error(f"[PRETIX] Reached PRETIX_REQUESTS_MAX ({PRETIX_REQUESTS_MAX}) while {opLogString} '{url}'. Aborting")
			raise httpx.TimeoutException(f"PRETIX_REQUESTS_MAX reached while {opLogString} to pretix.")

	return res