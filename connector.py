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
import logging

log = logging.getLogger()

def checkConfig():
    if (not DEV_MODE) and DUMMY_DATA:
        log.warn('It is strongly unadvised to use dummy data in production')

def getOrders(page):
    return None
        
def getOrder(code):
    return None