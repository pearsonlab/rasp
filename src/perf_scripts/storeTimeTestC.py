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

# Measure limbo.put(), pyarrow put and plasma store memory usage


def f1():
    data = np.arange(100000, dtype="int64")
    tensor = pa.Tensor.from_numpy(data)

    object_id = plasma.ObjectID(np.random.bytes(20))
    data_size = pa.get_tensor_size(tensor)
    buf = client.create(object_id, data_size)
    stream = pa.FixedSizeBufferWriter(buf)
    pa.write_tensor(tensor, stream)
    client.seal(object_id)


def f2():
    data = np.arange(100000, dtype="int64")
    limbo.put(data, "arr")


if __name__ == '__main__':
    subprocess.Popen(['plasma_store_server', '-s', '/tmp/store','-m', str(1000000000)])
    client = plasma.connect("/tmp/store","",0)
    times1 = []
    mems1 = []
    times2 = []
    mems2 = []

    # PYARROW TEST
    for i in range(1000):
        print("Obj: " + str(i))

        PROCNAME = "plasma_store_server"
        for proc in psutil.process_iter():
            if proc.name() == PROCNAME:
                break

        times1.append(timeit.timeit('f1()', setup="from __main__ import f1", number=1))
        mems1.append(proc.memory_info().rss)

    os.system('killall plasma_store_server')
    subprocess.Popen(['plasma_store_server', '-s', '/tmp/store','-m', str(1000000000)])
    time.sleep(1)

    # LIMBO TEST
    limbo = store.Limbo()
    for i in range(1000):
        print("Obj: " + str(i))

        PROCNAME = "plasma_store_server"
        for proc in psutil.process_iter():
            if proc.name() == PROCNAME:
                break
                
        times2.append(timeit.timeit('f2()', setup="from __main__ import f2", number=1))
        mems2.append(proc.memory_info().rss)

    os.system('killall plasma_store_server')

    # PLOT GRAPH
    sizes = list(range(len(times1)))
    f, (ax1, ax2) = plt.subplots(1, 2)
    ax1.plot(sizes, times1, linestyle="-", marker=".", color="blue", label="pyarrow")
    ax1.plot(sizes, times2, linestyle="-", marker=".", color="orange", label="limbo")
    ax2.plot(sizes, mems1, linestyle="-", marker=".", color="blue", label="pyarrow")
    ax2.plot(sizes, mems2, linestyle="-", marker=".", color="orange", label="limbo")
    ax1.set_title("limbo, pyarrow Timings")
    ax1.set_xlabel("Obj #")
    ax1.set_ylabel("Time (s)")
    ax2.set_title("plasma_store_server Memory Usage")
    ax2.set_xlabel("Obj #")
    ax2.set_ylabel("Memory used (MB)")
    plt.show()



