from os import getenv
from threading import Timer
from constants import SHORT_KEY, LONG_KEY, BATCH_INSERT_TIME, URL_TABLE_NAME
import cassandra_util as cassandraUtil
import redis_util as redisUtil

from fastapi import FastAPI, Form, Request, File, HTTPException
from fastapi.responses import PlainTextResponse, HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# USAGE
# curl -v 'http://10.11.12.115:80/hello'
# curl -v -X PUT 'http://10.11.12.115:80/?short=hello&long=goodbye'
app = FastAPI()
# app = Flask(__name__)

BATCH_PUTS = []

# optional, required if you are serving webpage via template engine
templates = Jinja2Templates(directory="templates")

@app.get('/{shortVal}', response_class=HTMLResponse)
async def getRoute(request: Request, shortVal):
    # Check in redis cache first and then cassandra
    try: 
        longVal = redisUtil.getCache(shortVal)
        print("Redis return: " + str(longVal))
        if longVal:
            return RedirectResponse(longVal)
    except Exception as e:
        # Do not return 500 here as a cache failure isnt too important
        print('Redis error: trouble connecting')
        print(repr(e))

    try:
        longVal = cassandraUtil.get(shortVal)
        if not longVal:
            return  templates.TemplateResponse('404.html', {"request": request, "message": 404}) 
    except: 
        print('Cassandra error: trouble connecting')
        return templates.TemplateResponse('500.html', {"request": request, "message": 500}) 

    try:
        redisUtil.putCache(shortVal, longVal)
    except:
        # We should still redirect even if redis cache failed
        return RedirectResponse(longVal)

    return RedirectResponse(longVal)

@app.put('/')
async def putRoute(short: str, long:str, request: Request):
  
 
    BATCH_PUTS.append(
        "INSERT INTO {} ({}, {}) VALUES ('{}', '{}');".format(
            URL_TABLE_NAME, SHORT_KEY, LONG_KEY, short, long))
    
    return templates.TemplateResponse('200.html', {"request": request, "message": 200}) 

@app.route('/', methods=['GET','POST','DELETE'])
@app.route('/<path:path>', methods=['GET','PUT','POST','DELETE'])
def unauthorized(path=''):
    return templates.TemplateResponse('unauthorized.html', {"request": request, "message": 400}) 

def intervalBatchPut():
    # Every BATCH_INSERT_TIME seconds, call this function again in a new thread
    thread = Timer(BATCH_INSERT_TIME, intervalBatchPut)
    thread.daemon = True
    thread.start()

    global BATCH_PUTS
    if len(BATCH_PUTS) == 0:
        return

    try:
        cassandraUtil.batchPut(BATCH_PUTS)
        BATCH_PUTS = []
    except:
        print('Cassandra error: issue inserting batch put. Trying again.')
    
intervalBatchPut()
