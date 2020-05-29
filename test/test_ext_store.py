import multiprocessing
import os
import pytest
import random
import signal
import struct
import subprocess
import sys
import time

import numpy as np
import pyarrow as pa


DEFAULT_PLASMA_STORE_MEMORY = 10 ** 8
USE_VALGRIND = os.getenv("PLASMA_VALGRIND") == "1"
EXTERNAL_STORE = "hashtable://test"
SMALL_OBJECT_SIZE = 9000

def random_object_id():
    import pyarrow.plasma as plasma
    return plasma.ObjectID(np.random.bytes(20))

@pytest.mark.plasma
class TestEvictionToExternalStore:

    def setup_method(self, test_method):
        import pyarrow.plasma as plasma
        # Start Plasma store.
        self.plasma_store_ctx = plasma.start_plasma_store(
            plasma_store_memory=1000 * 1024,
            use_valgrind=USE_VALGRIND,
            external_store=EXTERNAL_STORE)
        self.plasma_store_name, self.p = self.plasma_store_ctx.__enter__()
        # Connect to Plasma.
        self.plasma_client = plasma.connect(self.plasma_store_name)

    def teardown_method(self, test_method):
        try:
            # Check that the Plasma store is still alive.
            assert self.p.poll() is None
            self.p.send_signal(signal.SIGTERM)
            self.p.wait(timeout=5)
        finally:
            self.plasma_store_ctx.__exit__(None, None, None)

    def test_eviction(self):
        client = self.plasma_client

        object_ids = [random_object_id() for _ in range(0, 20)]
        data = b'x' * 100 * 1024
        metadata = b''

        for i in range(0, 20):
            # Test for object non-existence.
            assert not client.contains(object_ids[i])

            # Create and seal the object.
            client.create_and_seal(object_ids[i], data, metadata)

            # Test that the client can get the object.
            assert client.contains(object_ids[i])

        for i in range(0, 20):
            # Since we are accessing objects sequentially, every object we
            # access would be a cache "miss" owing to LRU eviction.
            # Try and access the object from the plasma store first, and then
            # try external store on failure. This should succeed to fetch the
            # object. However, it may evict the next few objects.
            [result] = client.get_buffers([object_ids[i]])
            assert result.to_pybytes() == data

        # Make sure we still cannot fetch objects that do not exist
        [result] = client.get_buffers([random_object_id()], timeout_ms=100)
        assert result is None
