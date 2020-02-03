import pyarrow.plasma as plasma 
import pyarrow as pa
import numpy as np
import timeit
import sys

def f1():
    client = plasma.connect("/tmp/store","",0)
    ids = []

    for i in range(100):
        data = np.arange(10, dtype="int64")
        arr = pa.array(data)

        objId = plasma.ObjectID(np.random.bytes(20))
        dataSize = data.nbytes

        ids.append(objId)
        buf = client.create(objId, dataSize)
        client.seal(objId)

def f2():
    client = plasma.connect("/tmp/store","",0)
    ids = []

    for i in range(100):
        data = np.arange(100, dtype="int64")
        arr = pa.array(data)

        objId = plasma.ObjectID(np.random.bytes(20))
        dataSize = data.nbytes

        ids.append(objId)
        buf = client.create(objId, dataSize)
        client.seal(objId)

def f3():
    client = plasma.connect("/tmp/store","",0)
    ids = []

    for i in range(100):
        data = np.arange(1000, dtype="int64")
        arr = pa.array(data)

        objId = plasma.ObjectID(np.random.bytes(20))
        dataSize = data.nbytes

        ids.append(objId)
        buf = client.create(objId, dataSize)
        client.seal(objId)

def f4():
    client = plasma.connect("/tmp/store","",0)
    ids = []

    for i in range(100):
        data = np.arange(10000, dtype="int64")
        arr = pa.array(data)

        objId = plasma.ObjectID(np.random.bytes(20))
        dataSize = data.nbytes

        ids.append(objId)
        buf = client.create(objId, dataSize)
        client.seal(objId)

def f5():
    client = plasma.connect("/tmp/store","",0)
    ids = []

    for i in range(100):
        data = np.arange(100000, dtype="int64")
        arr = pa.array(data)

        objId = plasma.ObjectID(np.random.bytes(20))
        dataSize = data.nbytes

        ids.append(objId)
        buf = client.create(objId, dataSize)
        client.seal(objId)


if __name__ == '__main__':
    d = np.arange(10, dtype="int64")
    print(sys.getsizeof(d))
    print("f1() " + str(timeit.timeit('f1()', setup="from __main__ import f1", number=100)))
    d = np.arange(100, dtype="int64")
    print(sys.getsizeof(d))
    print("f2() " + str(timeit.timeit('f2()', setup="from __main__ import f2", number=100)))
    d = np.arange(1000, dtype="int64")
    print(sys.getsizeof(d))
    print("f3() " + str(timeit.timeit('f3()', setup="from __main__ import f3", number=100)))
    d = np.arange(10000, dtype="int64")
    print(sys.getsizeof(d))
    print("f4() " + str(timeit.timeit('f4()', setup="from __main__ import f4", number=100)))
    d = np.arange(100000, dtype="int64")
    print(sys.getsizeof(d))
    print("f5() " + str(timeit.timeit('f5()', setup="from __main__ import f5", number=100)))