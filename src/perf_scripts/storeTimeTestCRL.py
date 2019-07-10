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

def fGet():
    data = np.arange(100000, dtype="int64")
    object_id = limbo.put(data, str(i))
    ids.append(object_id)
    names.append(str(i))
    print("OBJ GET " + str(i) + ": " + str(ids[i]))

def fRet():
    objs.append(limbo.get(names[i]))
    print("OBJ RET " + str(i) + ": " + str(ids[i]))


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
        timesG.append(timeit.timeit('fGet()', setup="from __main__ import fGet", number=1))
        timesR.append(timeit.timeit('fRet()', setup="from __main__ import fRet", number=1))
        mems[i] = proc.memory_info().rss

    p.kill()

    mems = np.divide(mems, 1000000)

    # PLOT GRAPH
    sizes = list(range(len(timesG)))
    f, (ax1, ax2) = plt.subplots(1, 2)
    ax1.plot(sizes, timesG, linestyle="-", marker=".", color="orange", label="Get")
    ax1.plot(sizes, timesR, linestyle="-", marker=".", color="blue", label="Ret")
    ax2.plot(sizes, mems, linestyle="-", marker=".", color="green")
    ax1.set_title("limbo.put(), limbo.get() Timings")
    ax1.set_xlabel("Obj #")
    ax1.set_ylabel("Time (s)")
    ax2.set_title("plasma_store_server Memory Usage")
    ax2.set_xlabel("Obj #")
    ax2.set_ylabel("Memory used (MB)")
    plt.show()