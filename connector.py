# To connect with pretix's data
# WIP to not commit
# DrewTW
import string
import httpx
import json
from ext import *
from config import *
from sanic import response
from sanic import Blueprint
from sanic.log import logger

def checkConfig():
    if (not DEV_MODE) and DUMMY_DATA:
        logger.warn('It is strongly unadvised to use dummy data in production')

def getOrders(page):
    return None
        
def getOrder(code):
    return None