import pyarrow.plasma as plasma 
import pyarrow as pa
import numpy as np
import timeit
import sys
from nexus import store

def f1(n):
    limbo = store.Limbo()

    for i in range(100000):
        print("Obj: " + str(i))

        data = np.arange(n, dtype="int64")
        limbo.put(data, "arr")


if __name__ == '__main__':
    client = plasma.connect("/tmp/store","",0)
    
    arr_size = 100000
    f1(arr_size)

    print(client.list())
