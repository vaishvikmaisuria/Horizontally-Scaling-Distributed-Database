#!/bin/bash
USAGE="Usage: $0 IP1 IP2 IP3 ..."

if [ "$#" == "0" ]; then
	echo "$USAGE"
	exit 1
fi

i=0
MASTER="$1"
while (( "$#" )); do
	if [ "$1" = "$MASTER" ]; 
	then
		COMMAND="docker run --name cassandra-node-$i -d -e CASSANDRA_BROADCAST_ADDRESS=$1 -p 7000:7000 -p 9042:9042 cassandra"
	else
		COMMAND="docker run --name cassandra-node-$i -d -e CASSANDRA_BROADCAST_ADDRESS=$1 -p 7000:7000 -p 9042:9042 -e CASSANDRA_SEEDS=$MASTER cassandra"
	fi
	ssh student@$1 "docker container stop cassandra-node-$i"
	ssh student@$1 "docker container rm cassandra-node-$i"
	ssh student@$1 "$COMMAND"
	
	while true;
	do
		sleep 5
		STATUS=$(docker exec -it cassandra-node-0 nodetool status | grep -e $1)
		STATUSUN=$(echo $STATUS | grep -e $1)
		echo $STATUS
		[[ ! -z "$STATUSUN" ]] && break;
	done;
    i=$((i+1))
	shift
done