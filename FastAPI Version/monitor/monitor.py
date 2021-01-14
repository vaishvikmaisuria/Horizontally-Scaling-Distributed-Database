import time
import subprocess
import shlex
import os
import threading
from subprocess import PIPE
from os import getenv
from threading import Timer
from configparser import ConfigParser
from flask import Flask, request, redirect, render_template, session
from flask_table import Table, Col

app = Flask(__name__)

config = ConfigParser()
config.read('../config.ini')
nodes = config['DEFAULT']['ips']
ips = nodes.split(',')

INFO = {}
command = "ssh {} docker stats --no-stream"

class Item(object):
    def __init__(self, containerID, name, cpu, memUsage, memPer, netIO, blockIO, pids):
        self.name = name
        self.containerID = containerID
        self.cpu = cpu
        self.memUsage = memUsage
        self.memPer = memPer
        self.netIO = netIO
        self.blockIO = blockIO
        self.pids = pids


class ItemTable(Table):
    containerID = Col(' CONTAINER ID ')
    name = Col(' NAME ')
    cpu = Col(' CPU% ')
    memUsage = Col(" MEM USAGE/LIMIT ")
    memPer = Col(" MEM% ")
    netIO = Col(" NET-I/O ")
    blockIO = Col(" Block-I/O ")
    pids = Col(" PIDS ")

    def get_tr_attrs(self, item):
        return {'class': 'important'}


def threadFunction(ip):
  global INFO
  p = subprocess.Popen(shlex.split(command.format(ip)), shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  output, err = p.communicate(b"input data that is passed to subprocess' stdin")
  p.wait()
  INFO[ip] = str(output.decode("utf-8"))
 

def updateFunction():
  threadList = []
  for i in ips:
    t = threading.Thread(target=threadFunction, args=[i])
    threadList.append(t)

  for t in threadList:
    t.start()
  for t in threadList:
    t.join()


def BreakInfo():
  global INFO
  items = []
  keys = INFO.keys()
  for key in keys:
    info = INFO[key]
    if (len(info) <= 1):
      continue

    info = info.split('\n')[1:]
    info = list(filter(None, info))
    for vals in info:
      vals = vals.replace(" / ","/")
      x = vals.split(" ")
      x = list(filter(None, x))
      i = Item(x[0], x[1],x[2], x[3],x[4], x[5],x[6], x[7])
      items.append(i)
  
  return  ItemTable(items)


def get_progress():
    global INFO
    updateFunction()
    table = BreakInfo()
    return {
        "node0": table.__html__(),
    }

@app.route("/")
def home():
  return render_template("index.html", **get_progress())
  # return "<html> <h1>Hello</h1> </html>"
    
if __name__ == '__main__':
  app.run(host='0.0.0.0', port=4000, threaded=True)
  
