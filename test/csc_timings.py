import timeit
import os
import sys
sys.path.append(".")
import matplotlib.pyplot as plt


from unittest import TestCase
from nexus.store import Limbo
from multiprocessing import Process
from scipy.sparse import csc_matrix
import numpy as np
import pyarrow.plasma as plasma
import pickle
import subprocess
from nexus.actor import RunManager, AsyncRunManager

# Time putting and getting a matrix to the store
# matrix is size (n x n)
# Type of the matrix can be "normal" (default) or "csc"

def time_putget(n, type = "normal"):
    # Start the process
    p = subprocess.Popen(['plasma_store',
                      '-s', '/tmp/store',
                      '-m', str(10000000000)],
                      stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL)
    limbo = Limbo()

    # Make an array of random integers in range [0,100) of size (n x n)
    data = np.random.randint(0,100,(n,n),dtype=np.int8)

    if (type == "csc"):
        matrix = csc_matrix(data)
    else:
        matrix = data

    # Print object size
    #size = sys.getsizeof(matrix)
    #print(size)
    size = matrix.data.nbytes
    print("Size: ", size)

    # Time putting and getting to store
    print("Putting {type} matrix of size {n} by {n}".format(type = type, n = n))
    t = timeit.default_timer()
    limbo.put(matrix, "matrix")
    putTime = timeit.default_timer() - t
    print('\tTime', putTime)



    print("Getting {type} matrix of size {n} by {n}".format(type = type, n = n))
    t = timeit.default_timer()
    limbo.get("matrix")
    getTime = timeit.default_timer() - t
    print('\tTime', getTime)

    # Kill the process
    p.kill()

    # Return timings

    return putTime, getTime, size



timings = {
    "csc": {
        "put": [],
        "get": [],
        "size": []
    },
    "normal": {
        "put": [],
        "get": [],
        "size": []
    }
}


def updateTimings(putTime, getTime, size, type = "normal"):
    timings[type]["put"].append(putTime)
    timings[type]["get"].append(getTime)
    timings[type]["size"].append(size)

# TODO: add timings up to 1gb
# Run results
for i in range(100,500):
    putTime, getTime, size = time_putget(i)
    updateTimings(putTime, getTime, size)

    putTime, getTime, size = time_putget(i, type = "csc")
    updateTimings(putTime, getTime, size, type = "csc")


print(timings)
# TODO: Plot results


def  plotTimings(type):
    putTimes = timings[type]["put"]
    getTimes = timings[type]["get"]
    sizes = timings[type]["size"]

    plt.plot(sizes, putTimes, label = "Put, {}".format(type))
    plt.plot(sizes, getTimes, label = "Get, {}".format(type))
    plt.ylabel("Time of operation (seconds)")
    plt.xlabel("Size of matrix (bytes)")


plotTimings("normal")
plotTimings("csc")
plt.legend()
plt.show()
