# Create cassandra cluster
#   Create keyspace
#   Create table
# If it already exists, remove and start again
# Should be able to stop the cassandra cluster

import sys
import subprocess
import time
from cassandra.cluster import Cluster
import configparser


startCommand = "ssh student@{} 'docker run -d --restart unless-stopped --name cassandra-node -v ~/cassandraNodeVolume:/var/lib/cassandra -d -e CASSANDRA_BROADCAST_ADDRESS={} -p 7000:7000 -p 9042:9042 {}cassandra'"
stopCommand = "ssh student@{} 'docker container stop cassandra-node'"
rmCommand = "ssh student@{} 'docker container rm cassandra-node'"
directoryBuild = "ssh -t student@{} 'sudo rm -rf ~/cassandraNodeVolume && mkdir ~/cassandraNodeVolume'"


# formatOutput converts a binary string into a normal string, and deletes the first line
def formatOutput(output):
    output = str(output, 'utf-8')
    output = output.split("\n")
    output.pop()
    return output


# checkStatus is used to check if there are upNodes up and running
def checkStatus(upNodes, nodeName):
    command = "docker exec -it {} nodetool status | grep 'UN'".format(nodeName)
    output = subprocess.check_output(command, shell=True)
    return len(formatOutput(output)) == upNodes

# setup Cassandra creates a keyspace and initializes the urlPair table in the given cluster session
def setupCassandra(session):
    session.execute("DROP KEYSPACE IF EXISTS urlShortener;")
    session.execute(
        "CREATE KEYSPACE urlShortener WITH replication = {'class': 'SimpleStrategy', 'replication_factor' : 3};")
    session.execute("CREATE TABLE urlShortener.urlPairs(short text PRIMARY KEY, long text);")

#getMasterNodeIP get the IP of the master node in a cluster (works only for local deploy)
def getMasterNodeIP(nodeName):
    command = "docker exec -it {} nodetool status | grep 'UN'".format(nodeName)
    output = subprocess.check_output(command, shell=True)
    output = formatOutput(output)
    print(output)
    IP = output[0].split('  ')[1]
    return IP


# clusterLocal starts up a cassandra cluster with numNodes
def clusterLocal(numNodes):
    with open("/tmp/output.log", "a") as output:
        print("Creating a Docker network")
        subprocess.call("docker network create mynet", shell=True, stdout=output, stderr=output)

        print("Starting node(master) ", 0)
        masterNodeName = "cas0"
        command = "docker run --name {} --network mynet -d cassandra".format(masterNodeName)
        subprocess.call(command, shell=True, stdout=None, stderr=None)
        time.sleep(15)
        # Wait until master node is up

        while not checkStatus(1, masterNodeName):
            pass

        IP = getMasterNodeIP(masterNodeName)
        print(IP)
        i = 1
        while i < numNodes:
            print("Starting node ", i)
            nodeName = 'cas' + str(i)
            command = "docker run --name {} --network mynet -d -e CASSANDRA_SEEDS={} cassandra".format(nodeName,
                                                                                                       masterNodeName)
            subprocess.call(command, shell=True, stdout=None, stderr=None)
            time.sleep(10)
            # Wait until master node is up
            while not checkStatus(i + 1, masterNodeName):
                pass

            i += 1

    cluster = Cluster(['localhost'], port=9042)
    session = cluster.connect()
    setupCassandra(session)


# networkStatusCheck, check if the given IP is up and running. This function can only be executed if the 
# masterNode is the current host pc
def networkStatusCheck(IP):
    with open("/tmp/output.log", "a") as output:
        command = "docker exec -it cassandra-node nodetool status | grep 'UN  {}'".format(IP)
        output = subprocess.call(command, shell=True, stdout=output, stderr=output)

        print("{} is up: {}".format(IP, output == 0))
        if output == 1:
            return False
        elif output == 0:
            return True


# clusterNetwork starts up a cassandra cluster on the given set of IPS
def clusterNetwork(nodes):
    # Note there is a way to send in a seperate storage path for the database
    global startCommand, directoryBuild, stopCommand, rmCommand

    masterSeed = "-e CASSANDRA_SEEDS={} ".format(nodes[0])
    for i in range(len(nodes)):
        subprocess.call(stopCommand.format(nodes[i]), shell=True)
        subprocess.call(rmCommand.format(nodes[i]), shell=True)
        subprocess.call(directoryBuild.format(nodes[i]), shell=True)

        if i == 0:
            # Master node
            subprocess.call(startCommand.format(nodes[i], nodes[i], ""), shell=True)
            time.sleep(5)
            # Adding a sleep of 5 so the master node has enough time to get configured before we start to make
            # status calls to it
        else:
            subprocess.call(startCommand.format(nodes[i], nodes[i], masterSeed), shell=True)

        while (not networkStatusCheck(nodes[i])):
            time.sleep(1)
            # Adding a sleep of 1, so we don't overload the node with status calls
            pass

    cluster = Cluster(nodes)
    session = cluster.connect()
    setupCassandra(session)


# stopCassandraNodesNetwork stops cassnadra docker containers
def stopCassandraNodesNetwork(nodes):
    global stopCommand, rmCommand
    for i in range(len(nodes)):
        subprocess.call(stopCommand.format(nodes[i], i), shell=True)
        subprocess.call(rmCommand.format(nodes[i], i), shell=True) 


# newNodeStatus goes into the master pc, and checks if IP is up and running normally
def newNodeStatus(IP, master):
    with open("/tmp/output.log", "a") as output:
        command = "ssh student@{} docker exec -i cassandra-node nodetool status | grep 'UN  {}'".format(master, IP)
        output = subprocess.call(command, shell=True, stdout=output, stderr=output)
        print("{} is up: {}".format(IP, output == 0))
        
        if output == 1:
            return False
        elif output == 0:
            return True

def updateConfigFile(updateType, IP):
    config = configparser.ConfigParser()
    config.read('../config.ini')
    nodes = config['DEFAULT']['cassandra_nodes']

    if updateType == 0:
        # removing a node
        nodes = nodes.split(",")
        nodes.pop(nodes.index(IP))
        nodes = ','.join(nodes)

        config['DEFAULT']['cassandra_nodes'] = nodes
        with open('../config.ini', 'w') as configFile:
            config.write(configFile)
        
    elif updateType == 1:
        #adding a node
        nodes = nodes + ',' + IP
        config['DEFAULT']['cassandra_nodes'] = nodes
        with open('../config.ini', 'w') as configFile:
            config.write(configFile)
    
    # subprocess.call('docker service update --force CSC409A2_web', shell=True)


# addNewNode add a new node to a existing cassandra cluster
def addNewNode(masterNode, newIP):
    
    global startCommand, directoryBuild, stopCommand, rmCommand
    
    if (not newNodeStatus(masterNode,masterNode)):
        print("Master Node is not up")
        exit(1)

    masterSeed = "-e CASSANDRA_SEEDS={} ".format(masterNode)
    # Need to get all the connected nodes
    getCommand = "ssh student@{} 'docker exec -i cassandra-node nodetool status'"
    
    status = subprocess.check_output(getCommand.format(masterNode), shell=True)
    status = str(status.decode("utf-8")).split('\n')[5:]
    status = list(filter(None, status))
    i = len(status) + 1

    subprocess.call(stopCommand.format(newIP), shell=True)
    subprocess.call(rmCommand.format(newIP), shell=True)
    subprocess.call(directoryBuild.format(newIP), shell=True)
    subprocess.call(startCommand.format(newIP, newIP, masterSeed), shell=True)
    
    masterNodeCounter = 0
    while (not newNodeStatus(newIP, masterNode)):
        time.sleep(1)
        masterNodeCounter += 1
        if masterNodeCounter > 10:
            #Check is master node is active
            status = newNodeStatus(masterNode, masterNode)
            if not status:
                print("Master node is Down (Master Node IP: {})".format(masterNode))
                exit(1)
            masterNodeCounter = 0
        # Adding a sleep of 1, so we don't overload the node with status calls
        pass
    
    updateConfigFile(1, newIP)

# removeLiveNode removes a runnning cassandra node, and distributes its data other nodes in cluster
def removeLiveNode(IP):
    decommision = "ssh student@{} docker exec -i cassandra-node nodetool decommission"
    stopCommand = "ssh student@{} 'docker container stop cassandra-node'"
    rmCommand = "ssh student@{} 'docker container rm cassandra-node'"

    print("Starting process to remove node {}".format(IP))
    
    print("Transfering all node data to other nodes")
    subprocess.call(decommision.format(IP), shell=True)
    
    print("Stopping and removing node container")
    subprocess.call(stopCommand.format(IP), shell=True)
    subprocess.call(rmCommand.format(IP), shell=True)

    updateConfigFile(0, IP)
    
    


def usage():
    print("USAGE: \n\
    python3 cassandraDeploy.py localhost <NUMBER OF NODES>\n\
    python3 cassandraDeploy.py network <IP1> <IP2> <IP3> ... <IPN>\n\
    python3 cassandraDeploy.py network clean <IP1> <IP2> <IP3> ... <IPN> \n \
    python3 cassandraDeploy.py network newNode <MasterIP> <newNodeIP>\n\
    python3 cassandraDeploy.py network rmNode <nodeIP>")


if __name__ == "__main__":

    if len(sys.argv) <= 1:
        usage()
        exit(1)
    clusterType = sys.argv[1]
    if clusterType == 'localhost':
        numNodes = int(sys.argv[2])
        clusterLocal(numNodes)
    elif clusterType == 'network' and sys.argv[2] == 'clean':
        nodes = sys.argv[3:]
        stopCassandraNodesNetwork(nodes)
    elif clusterType == 'network' and sys.argv[2] == 'newNode':
        addNewNode(sys.argv[3], sys.argv[4])
    elif clusterType == 'network' and sys.argv[2] == "rmNode":
        removeLiveNode(sys.argv[3])
    elif clusterType == 'network':
        nodes = sys.argv[2:]
        clusterNetwork(nodes)
    else:
        usage()
