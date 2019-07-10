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

def fGet():
    data = np.arange(100000, dtype="int64")
    object_id = client.put(data)
    ids.append(object_id)
    print("OBJ GET " + str(i) + ": " + str(ids[i]))

def fRet():
    objs.append(client.get(ids[i]))
    print("OBJ RET " + str(i) + ": " + str(ids[i]))


if __name__ == '__main__':
    p = subprocess.Popen(['plasma_store_server', '-s', '/tmp/store','-m', str(10000000000)])
    client = plasma.connect("/tmp/store","",0)
    timesG = []
    timesR = []
    mems = np.empty((1000,1))

    # CLIENT TEST
    for i in range(1000):
        PROCNAME = "plasma_store_server"
        for proc in psutil.process_iter():
            if proc.name() == PROCNAME:
                break               
        timesG.append(timeit.timeit('fGet()', setup="from __main__ import fGet", number=1))
        timesR.append(timeit.timeit('fRet()', setup="from __main__ import fRet", number=1))
        mems[i] = proc.memory_info().rss

    client.disconnect()
    p.kill()

    mems = np.divide(mems, 1000000)

    # PLOT GRAPH
    sizes = list(range(len(timesG)))
    f, (ax1, ax2) = plt.subplots(1, 2)
    ax1.plot(sizes, timesG, linestyle="-", marker=".", color="orange", label="Get")
    ax1.plot(sizes, timesR, linestyle="-", marker=".", color="blue", label="Ret")
    ax2.plot(sizes, mems, linestyle="-", marker=".", color="green")
    ax1.set_title("client.put(), client.get() Timings")
    ax1.set_xlabel("Obj #")
    ax1.set_ylabel("Time (s)")
    ax2.set_title("plasma_store_server Memory Usage")
    ax2.set_xlabel("Obj #")
    ax2.set_ylabel("Memory used (MB)")
    plt.show()