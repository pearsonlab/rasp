import pyarrow.plasma as plasma 
import pyarrow as pa
import numpy as np
import timeit
import time
import sys
import os
import subprocess
import store
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import psutil

# Measure limbo.put(), get() and plasma store memory usage

objs = []
ids = []
names = []

@profile
def fGet():
    data = np.arange(100000, dtype="int64")
    object_id = limbo.put(data, str(i))
    ids.append(object_id)
    names.append(str(i))
    #print("OBJ GET " + str(i) + ": " + str(ids[i]))

@profile
def fRet():
    objs.append(limbo.get(names[i]))
    #print("OBJ RET " + str(i) + ": " + str(ids[i]))


if __name__ == '__main__':
    p = subprocess.Popen(['plasma_store_server', '-s', '/tmp/store','-m', str(10000000000)])
    limbo = store.Limbo()
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

    p.kill()