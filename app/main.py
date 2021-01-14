from os import getenv
from threading import Timer
from flask import Flask, request, redirect, render_template
from constants import SHORT_KEY, LONG_KEY, BATCH_INSERT_TIME, URL_TABLE_NAME
import cassandra_util as cassandraUtil
import redis_util as redisUtil

# USAGE
# curl -v 'http://10.11.12.115:80/hello'
# curl -v -X PUT 'http://10.11.12.115:80/?short=hello&long=goodbye'

app = Flask(__name__)

BATCH_PUTS = []

@app.route('/<shortVal>', methods=['GET'])
def getRoute(shortVal):
    # Check in redis cache first and then cassandra
    try: 
        longVal = redisUtil.getCache(shortVal)
        print("Redis return: " + str(longVal))
        if longVal:
            return redirect(longVal, code=307)
    except Exception as e:
        # Do not return 500 here as a cache failure isnt too important
        print('Redis error: trouble connecting')
        print(repr(e))

    try:
        longVal = cassandraUtil.get(shortVal)
        if not longVal:
            return render_template('404.html'), 404
    except: 
        print('Cassandra error: trouble connecting')
        return render_template('500.html'), 500

    try:
        redisUtil.putCache(shortVal, longVal)
    except:
        # We should still redirect even if redis cache failed
        return redirect(longVal, code=307)

    return redirect(longVal, code=307)

@app.route('/', methods=['PUT'])
def putRoute():
    args = request.args

    if len(args) != 2 or SHORT_KEY not in args or LONG_KEY not in args:
        return unauthorized()

    shortVal = request.args[SHORT_KEY]
    longVal = request.args[LONG_KEY]
    
    BATCH_PUTS.append(
        "INSERT INTO {} ({}, {}) VALUES ('{}', '{}');".format(
            URL_TABLE_NAME, SHORT_KEY, LONG_KEY, shortVal, longVal))
    
    return render_template('200.html'), 200

@app.route('/', methods=['GET','POST','DELETE'])
@app.route('/<path:path>', methods=['GET','PUT','POST','DELETE'])
def unauthorized(path=''):
    return render_template('unauthorized.html'), 400

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
