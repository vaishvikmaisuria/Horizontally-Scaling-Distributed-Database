build :
	docker build -t url-shortener .
	cd app && pip3 install --trusted-host pypi.python.org -r requirements.txt
run : 
	docker swarm init --advertise-addr $(ip1) > worker.txt
	docker swarm join-token manager > manager.txt
start :
	docker stack deploy -c docker-compose.yml CSC409A2
start-local : 
	docker-compose -f docker-compose-local.yml up

save :
	docker tag url-shortener csc409group23/url:test
	docker push csc409group23/url:test

deployCC : # deploy cassandra Cluster 
	cd cassandra && python3 cassandraDeploy.py network $(ip1) $(ip2) $(ip3)

addNewCN: # Add new cassandra node
	cd cassandra && python3  cassandraDeploy.py network newNode $(ip1) $(ip2)
	docker service update --force CSC409A2_web

rmCNode: # Remove a cassandra node from cluster
	cd cassandra && python3  cassandraDeploy.py network rmNode $(ip1)
	docker service update --force CSC409A2_web

stopCassandra :
	cd cassandra && python3 cassandraDeploy.py network clean $(ip1) $(ip2) $(ip3)
clean :
	docker stack rm CSC409A2 || true 
	docker swarm leave --force || true 
	python3 pruneDocker.py network $(ip1) $(ip2) $(ip3)
cassandraState :
	docker exec -it cassandra-node nodetool status
monitor: 
	cd monitor && python3 monitor.py
