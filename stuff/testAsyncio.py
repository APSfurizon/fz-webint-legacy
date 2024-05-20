# python merda
import asyncio

async def a():
	print("a")

def b():
	loop = asyncio.get_event_loop()
	print(loop)

b()