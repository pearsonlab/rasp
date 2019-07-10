import pyarrow.plasma as plasma 
import pyarrow as pa
import numpy as np
import timeit
import time
import sys
import os
import subprocess
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import psutil

# Measure put(), get() and plasma store memory usage

objs = []
ids = []

@profile
def fGet():
    data = np.arange(100000, dtype="int64")
    object_id = client.put(data)
    ids.append(object_id)
    #print("OBJ GET " + str(i) + ": " + str(ids[i]))

@profile
def fRet():
    objs.append(client.get(ids[i]))
    #print("OBJ RET " + str(i) + ": " + str(ids[i]))


if __name__ == '__main__':
    p = subprocess.Popen(['plasma_store_server', '-s', '/tmp/store','-m', str(10000000000)])
    client = plasma.connect("/tmp/store","",0)
    timesG = []
    timesR = []
    mems = np.empty((1000,1))

    # LIMBO TEST
    for i in range(1000):
        PROCNAME = "plasma_store_server"
        for proc in psutil.process_iter():
            if proc.name() == PROCNAME:
                break               
        fGet()
        fRet()
        mems[i] = proc.memory_info().rss

    client.disconnect()
    p.kill()