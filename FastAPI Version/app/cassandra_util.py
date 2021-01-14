from cassandra.cluster import Cluster, BatchStatement, ConsistencyLevel
from configparser import ConfigParser
from constants import URL_TABLE_NAME, SHORT_KEY, KEYSPACE_NAME

config = ConfigParser()
config.read('config.ini')
nodes = config['DEFAULT']['cassandra_nodes']

cluster = Cluster(nodes.split(','))
session = cluster.connect(KEYSPACE_NAME)

def get(short):
    statement = "SELECT long FROM {} WHERE {}='{}';".format(URL_TABLE_NAME, SHORT_KEY, short)
    rows = session.execute(statement)
    longValLst = [row[0] for row in rows]
    if len(longValLst) == 0:
        return None
    return longValLst[0]

def batchPut(insertLst):
    batch = BatchStatement(consistency_level=ConsistencyLevel.QUORUM)

    for statement in insertLst:
        batch.add(statement)

    session.execute(batch)
