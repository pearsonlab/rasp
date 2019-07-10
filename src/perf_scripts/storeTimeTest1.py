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
    data = np.arange(100000, dtype="int64")
    tensor = pa.Tensor.from_numpy(data)

    object_id = plasma.ObjectID(np.random.bytes(20))
    data_size = pa.get_tensor_size(tensor)
    buf = client.create(object_id, data_size)
    stream = pa.FixedSizeBufferWriter(buf)
    pa.write_tensor(tensor, stream)
    client.seal(object_id)


if __name__ == '__main__':
    client = plasma.connect("/tmp/store","",0)
    timings = []

    for i in range(1000):
        print("Obj: " + str(i))
        timings.append(timeit.timeit('f1()', setup="from __main__ import f1", number=1))
        #print(client.list())

    #print(timings)

    sizes = list(range(len(timings)))

    plt.plot(sizes, timings, linestyle="-", marker="o", label="pyarrowT")
    #plt.scatter(sizes, pyarrowT, label="pyarrowT")
    plt.title("Times for plasma storage of # objs")
    plt.xlabel("Obj #")
    plt.ylabel("Execution time (s)")
    plt.show()



