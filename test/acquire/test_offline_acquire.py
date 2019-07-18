import pickle
import shutil
import time
import unittest

import lmdb
import numpy as np

from src.acquire.offline_acquire import LMDBAcquirer


class TestLMDBAcquirer(unittest.TestCase):
    """
    Test if LMDBAcquirer can extract raw frames that start with 'acq_raw' from LMDB
    and if these are indexed properly. The DB is generated in this script as well.

    """

    FRAME_SIZE = (100, 10, 10)
    TEST_DB_DIR = 'lmdb_test'

    def setUp(self):

        try:
            self.tearDown()
        except FileNotFoundError:
            pass

        self.frames = np.random.random(self.FRAME_SIZE)
        self.make_test_db()
        self.acquirer = LMDBAcquirer(name='test', lmdb_path=self.TEST_DB_DIR)

    def make_test_db(self):
        """ Generate new LMDB with Acquirer q_in keys. """

        with lmdb.open(self.TEST_DB_DIR, map_size=1e10) as lmdb_env:
            with lmdb_env.begin(write=True) as txn:
                for i, frame in enumerate(self.frames):
                    put_key = b''.join([f'acq_raw{i}'.encode(), pickle.dumps(time.time())])
                    txn.put(put_key, pickle.dumps(frame), overwrite=True)
                txn.put(b'gibberish1', b'thou shalt not see this', overwrite=True)

    def test_read_lmdb(self):
        """ Check first and last frame. """

        self.acquirer.setup()

        self.assert_(np.array_equal(self.frames[0], self.acquirer.getFrame(0)))
        last_frame = self.FRAME_SIZE[0] - 1
        self.assert_(np.array_equal(self.frames[last_frame], self.acquirer.getFrame(last_frame)))

    def tearDown(self):
        shutil.rmtree(self.TEST_DB_DIR)


if __name__ == '__main__':
    unittest.main()
