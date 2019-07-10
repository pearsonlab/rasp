import pyarrow.plasma as plasma 
import pyarrow as pa
import numpy as np
import timeit
import sys

def f1(n):
    ids = []

    for i in range(1):
        print("Obj: " + str(i))

        data = np.arange(n, dtype="int64")
        tensor = pa.Tensor.from_numpy(data)

        object_id = plasma.ObjectID(np.random.bytes(20))
        ids.append(object_id)
        data_size = pa.get_tensor_size(tensor)
        print(data_size)
        print(sys.getsizeof(tensor))
        buf = client.create(object_id, data_size)
        stream = pa.FixedSizeBufferWriter(buf)
        pa.write_tensor(tensor, stream)
        client.seal(object_id)

    return ids

def f1R(ids):
    buff = client.get_buffers(ids)
    reader = pa.BufferReader(buff[0])
    arr = pa.read_tensor(reader)
    return arr.to_numpy()
    

if __name__ == '__main__':
    client = plasma.connect("/tmp/store","",0)

    arr_size = 100000
    objIds = f1(arr_size)

    print(client.list())
    #print(f1R(objIds))
