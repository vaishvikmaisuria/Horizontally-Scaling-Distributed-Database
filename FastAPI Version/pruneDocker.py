import subprocess
import sys

containerStop = "docker stop $(docker ps -aq)"
containerRm = "docker rm $(docker ps -aq)"
volumePrune = "docker volume prune -f"
networkPrune = "docker network prune -f"


def localPrune():
    subprocess.call(containerStop, shell=True)
    subprocess.call(containerRm, shell=True)
    subprocess.call(volumePrune, shell=True)
    subprocess.call(networkPrune, shell=True)


def networkPrune(nodes):
    command = "ssh student@{} '{}'"

    for node in nodes:
        subprocess.call(command.format(node, containerStop), shell=True)
        subprocess.call(command.format(node, containerRm), shell=True)
        subprocess.call(command.format(node, volumePrune), shell=True)
        subprocess.call(command.format(node, networkPrune), shell=True)


if __name__ == "__main__":

    if len(sys.argv) <= 1:
        print("USAGE: python3 pruneDocker.py localhost\npython3 pruneDocker.py network <IP1> <IP2> ... <IPN>")

    if sys.argv[1] == 'network':
        networkPrune(sys.argv[2:])
    elif sys.argv[1] == 'localhost':
        localPrune()