import os
import random
import shutil
import string
import time
import unittest

import pyarrow.plasma as plasma

from src.nexus.store import LMDBStore


class TestLMDBStore(unittest.TestCase):
    """
    Test nexus.store.LMDBStore
    Check for functional puts/gets with and without object ID.

    """

    LMDB_NAME = 'test_lmdb_store'

    def setUp(self) -> None:
        self.tearDown()
        self.commit_freq = 20
        self.test_obj = b'test_obj'

    def test_construction_errors(self):

        with self.assertRaises(FileNotFoundError):
            LMDBStore(path='/magic_land')

        with self.assertRaises(FileExistsError):
            os.mkdir('./test_lmdb_exists')
            LMDBStore(path='./', name='test_lmdb_exists')
            os.removedirs('./test_lmdb_exists')

    def test_standalone(self):
        self.lmdb_store = LMDBStore(path='./', name=self.LMDB_NAME, commit_freq=self.commit_freq, from_limbo=False)
        self.lmdb_helper(rand_id=None)

    def test_from_limbo(self):
        self.lmdb_store = LMDBStore(path='./', name=self.LMDB_NAME, commit_freq=self.commit_freq, from_limbo=True)
        self.lmdb_helper(rand_id=plasma.ObjectID.from_random)

    @staticmethod
    def gen_rand_str(length=10):
        """Generate a random string of fixed length """

        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for _ in range(length))

    def lmdb_helper(self, rand_id=None):
        """
        Must generate self.lmdb_store with appropriate params first.

        :param rand_id: Function to generate object ID. None means object IDs are not used
                        (standalone case).

        """

        keys = []
        key_gen = rand_id if rand_id is not None else TestLMDBStore.gen_rand_str

        # For compatibility with both w/ and w/o object ID
        def gen_id():
            if rand_id is None:
                return None
            return keys[-1]

        def gen_name():
            if rand_id is None:
                return keys[-1]
            return TestLMDBStore.gen_rand_str()

        # Test if objects are being cached.
        for i in range(self.commit_freq):
            keys.append(key_gen())
            self.lmdb_store.put(self.test_obj, gen_name(), obj_id=gen_id())

        self.lmdb_store.lmdb_env.sync()  # Forces immediate disk write
        time.sleep(0.2)
        self.assertEqual(self.lmdb_store.get(keys[0]), None)

        # Over the threshold, should be written now.
        keys.append(key_gen())
        self.lmdb_store.put(self.test_obj, gen_name(), obj_id=gen_id())
        self.lmdb_store.lmdb_env.sync()
        time.sleep(0.2)
        self.assertEqual(self.lmdb_store.get(keys[-1]), self.test_obj)

        # Test 'flush_this_immediately'
        keys.append(key_gen())
        self.lmdb_store.put(self.test_obj, gen_name(), obj_id=gen_id(), flush_this_immediately=True)
        time.sleep(0.2)
        self.assertEqual(self.lmdb_store.get(keys[-1]), self.test_obj)

        # Test everything 'flush_immediately'
        self.lmdb_store.flush_immediately = True

        for i in range(3):
            keys.append(key_gen())
            self.lmdb_store.put(self.test_obj, gen_name(), obj_id=gen_id())
            time.sleep(0.2)
            self.assertEqual(self.lmdb_store.get(keys[-1]), self.test_obj)

    def tearDown(self):
        try:
            shutil.rmtree(f'./{self.LMDB_NAME}')
        except FileNotFoundError:
            pass


if __name__ == '__main__':
    unittest.main()
