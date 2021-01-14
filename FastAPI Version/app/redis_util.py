from redis import Redis, RedisError
from configparser import ConfigParser
from constants import CACHE_TTL, REDIS_MASTER_PASSWORD, REDIS_REPLICA_PASSWORD

config = ConfigParser()
config.read('config.ini')

redisMaster = None
redisReplicas = []

def setup(master, replicas):
    global redisMaster
    global redisReplicas

    try:
        redisMaster = Redis(host=master, port=6379, db=0, password=REDIS_MASTER_PASSWORD)
    except Exception as e:
        print('Redis: cannot update master node to host {}'.format(master))
        print(repr(e)) 

    for hostName in replicas:
        try:
            redisReplica = Redis(host=hostName, port=6379, db=0, password=REDIS_REPLICA_PASSWORD)
            redisReplicas.append(redisReplica)
        except Exception as e:
            print('Redis: cannot add replica node with host name {}'.format(hostName))
            print(repr(e))

def getCache(short):
    try:
        val = redisMaster.get(short)
        if val:
            # Reset time in cache
            redisMaster.expire(short, CACHE_TTL)
        return val
    except Exception as e:
        print('Redis: cannot connect to master node. Attempting replicas')
        print(repr(e))
        return getReplicas(short)

def getReplicas(short):
    for replica in redisReplicas:
        try:
            return replica.get(short)
        except Exception as e:
            print('Redis: cannot connect to replica node {}'.format(replica))
            print(repr(e))

def putCache(short, long):
    if redisMaster:
        redisMaster.set(short, long)
        redisMaster.expire(short, CACHE_TTL)
    else:
        print('Redis: master node not set. Cannot put {}, {}'.format(short, long))

master = config['DEFAULT']['redis_master']
replicas = config['DEFAULT']['redis_replicas']
setup(master, replicas.split(','))
