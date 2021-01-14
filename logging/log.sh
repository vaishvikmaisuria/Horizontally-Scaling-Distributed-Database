#!/bin/bash

mapfile -t id_array < <( docker service ls --format "{{.ID}}" )
for i in "${id_array[@]}"
do
    docker service logs -f $i &>> $i.out &
done


