import pyarrow.plasma as plasma 
import pyarrow as pa
import numpy as np
import timeit
import sys

if __name__ == '__main__':
    client = plasma.connect("/tmp/store","",0)

    a = np.arange(100000, dtype="int64")
    b = pa.array(np.arange(100000, dtype="int64"))
    print(sys.getsizeof(a))
    print(sys.getsizeof(b))
    print(a)
    print(b)
