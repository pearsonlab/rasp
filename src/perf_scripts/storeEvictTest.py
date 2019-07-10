import pyarrow.plasma as plasma 
import pyarrow as pa
import numpy as np
import timeit
import time
import sys
import os
import subprocess
from nexus import store
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import psutil

# Measure limbo.put(), get() and plasma store memory usage

objs = []
ids = []
names = []

def fPut():
    data = np.arange(100000, dtype="int64")
    object_id = limbo.put(data, str(i))
    ids.append(object_id)
    names.append(str(i))
    #print("OBJ PUT " + str(i) + ": " + str(ids[i]))

def fGet():
    objs.append(limbo.get(names[i]))
    #print("OBJ GET " + str(i) + ": " + str(ids[i]))


if __name__ == '__main__':
    p = subprocess.Popen(['plasma_store_server', '-s', '/tmp/store','-m', str(1000000000)])
    limbo = store.Limbo()
    timesP = []
    timesG = []

    # LIMBO TEST
    for i in range(1000):
        timesP.append(timeit.timeit('fPut()', setup="from __main__ import fPut", number=1))

    for i in range(1000):
        timesG.append(timeit.timeit('fGet()', setup="from __main__ import fGet", number=1))


    # PLOT GRAPH
    sizes = list(range(len(timesP)))
    plt.scatter(sizes, timesP, linestyle="-", marker=".", color="orange", label="Put") 
    plt.scatter(sizes, timesG, linestyle="-", marker=".", color="blue", label="Get")
    plt.title("limbo.put(), limbo.get() Timings")
    plt.xlabel("Obj #")
    plt.ylabel("Time (s)")
    plt.show()

    p.kill()