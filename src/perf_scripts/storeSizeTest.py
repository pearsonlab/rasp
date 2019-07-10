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

# Find obj # where lag jump occurs

objs = []
ids = []
names = []

def fGetC():
    data = np.arange(100000, dtype="int64")
    object_id = client.put(data)
    ids.append(object_id)
    #print("OBJ GET " + str(i) + ": " + str(ids[i]))

def fRetC():
    objs.append(client.get(ids[i]))
    #print("OBJ RET " + str(i) + ": " + str(ids[i]))

def fGetL():
    data = np.arange(100000, dtype="int64")
    object_id = limbo.put(data, str(i))
    names.append(str(i))
    #print("OBJ GET " + str(i) + ": " + str(ids[i]))

def fRetL():
    objs.append(limbo.get(names[i]))
    #print("OBJ RET " + str(i) + ": " + str(ids[i]))


if __name__ == '__main__':
    reps = 10000

    # plasma store management
    p = subprocess.Popen(['plasma_store_server', '-s', '/tmp/store','-m', str(10000000000)])
    client = plasma.connect("/tmp/store","",0)

    # Variable initialization
    timesGC = np.empty((reps,1))
    timesRC = np.empty((reps,1))
    timesGL = np.empty((reps,1))
    timesRL = np.empty((reps,1))
    memsC = np.empty((reps,1))
    memsL = np.empty((reps,1))

    # CLIENT TEST
    for i in range(reps):
        PROCNAME = "plasma_store_server"
        for proc in psutil.process_iter():
            if proc.name() == PROCNAME:
                break               
        timesGC[i] = timeit.timeit('fGetC()', setup="from __main__ import fGetC", number=1)
        timesRC[i] = timeit.timeit('fRetC()', setup="from __main__ import fRetC", number=1)
        memsC[i] = proc.memory_info().rss

    # plasma store management
    client.disconnect()
    p.kill()
    p = subprocess.Popen(['plasma_store_server', '-s', '/tmp/store','-m', str(10000000000)])
    limbo = store.Limbo()
    time.sleep(1)
    objs = []
    ids = []
    names = []

    # LIMBO TEST
    for i in range(reps):
        PROCNAME = "plasma_store_server"
        for proc in psutil.process_iter():
            if proc.name() == PROCNAME:
                break               
        timesGL[i] = timeit.timeit('fGetL()', setup="from __main__ import fGetL", number=1)
        timesRL[i] = timeit.timeit('fRetL()', setup="from __main__ import fRetL", number=1)
        memsL[i] = proc.memory_info().rss

    # Get megabytes
    memsC = np.divide(memsC, 1000000)
    memsL = np.divide(memsL, 1000000)
    timesGC = np.multiply(timesGC, 1000)
    timesRC = np.multiply(timesRC, 1000)
    timesGL = np.multiply(timesGL, 1000)
    timesRL = np.multiply(timesRL, 1000)


    timesGCJump = timesGC[timesGC > 10]
    timesRCJump = timesRC[timesRC > 0.5]
    timesGLJump = timesGL[timesGL > 10]
    timesRLJump = timesRL[timesRL > 0.5]
    timesGCJumpI = np.where(timesGC > 15)
    timesRCJumpI = np.where(timesRC > 3)
    timesGLJumpI = np.where(timesGL > 10)
    timesRLJumpI = np.where(timesRL > 10)

    print(timesGCJump)
    print(timesRCJump)
    print(timesGLJump)
    print(timesRLJump)
    print(timesGCJumpI)
    print(timesRCJumpI)
    print(timesGLJumpI)
    print(timesRLJumpI)


    # PLOT GRAPH
    sizes = list(range(len(timesGL)))
    f, (ax1, ax2) = plt.subplots(1, 2)
    ax1.plot(sizes, timesGC, linestyle="-", marker=".", color="orange", label="client.put()")
    ax1.plot(sizes, timesRC, linestyle="-", marker=".", color="red", label="client.get()")
    ax1.plot(sizes, timesGL, linestyle="-", marker=".", color="cyan", label="limbo.put()")
    ax1.plot(sizes, timesRL, linestyle="-", marker=".", color="blue", label="limbo.get()")
    ax2.plot(sizes, memsC, linestyle="-", marker=".", color="green", label="Client")
    ax2.plot(sizes, memsL, linestyle="-", marker=".", color="lime", label="Limbo")
    ax1.legend(loc="upper right")
    ax2.legend(loc="upper right")
    ax1.set_title("Put() and Get() Timings")
    ax1.set_xlabel("Obj #")
    ax1.set_ylabel("Time (ms)")
    ax2.set_title("plasma_store_server Memory Usage")
    ax2.set_xlabel("Obj #")
    ax2.set_ylabel("Memory used (MB)")
    plt.show()