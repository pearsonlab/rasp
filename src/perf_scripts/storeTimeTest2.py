import pyarrow.plasma as plasma 
import pyarrow as pa
import numpy as np
import timeit
import sys
from nexus import store
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np

def f1():
    limbo = store.Limbo()

    data = np.arange(100000, dtype="int64")
    limbo.put(data, "arr")


if __name__ == '__main__':
    client = plasma.connect("/tmp/store","",0)
    timings = []

    for i in range(1000):
        print("Obj: " + str(i))
        timings.append(timeit.timeit('f1()', setup="from __main__ import f1", number=1))
        #print(client.list())

    #print(timings)

    sizes = list(range(len(timings)))

    plt.plot(sizes, timings, linestyle="-", marker="o", label="limboT")
    #plt.scatter(sizes, pyarrowT, label="pyarrowT")
    plt.title("Times for plasma storage of # objs")
    plt.xlabel("Obj #")
    plt.ylabel("Execution time (s)")
    plt.show()



