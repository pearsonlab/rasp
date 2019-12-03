import timeit
import os
import sys
sys.path.append(".")

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
                      '-m', str(1E10)],
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
    print(matrix.data.nbytes)

    # Time putting and getting to store
    print("Putting {type} matrix of size {n} by {n}".format(type = type, n = n))
    t = timeit.default_timer()
    limbo.put(matrix, "matrix")
    print('\tTime', timeit.default_timer() - t)

    print("Getting {type} matrix of size {n} by {n}".format(type = type, n = n))
    t = timeit.default_timer()
    limbo.get("matrix")
    print('\tTime', timeit.default_timer() - t)

    # Kill the process
    p.kill()



# TODO: add timings up to 1gb
# Run results
for i in range(8000,8005):
    time_putget(i)
    time_putget(i, type = "csc")


# TODO: Plot results
