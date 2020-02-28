import numbers
import os
import pickle
from contextlib import contextmanager
from typing import Dict, Set
import lmdb
from .utils import get_num_length_from_key


class LMDBReader():
    def __init__(self, path):
        ''' Constructor for the LMDB reader
            path: Path to LMDB folder
        '''
        if not os.path.exists(path):
            raise FileNotFoundError
        self.path = path

    def get_all_data(self):
        ''' Load all data from LMDB into a dictionary
            Make sure that the LMDB is small enough to fit in RAM
        '''
        with LMDBReader._lmdb_cur(self.path) as cur:
            return {LMDBReader._decode_key(key): pickle.loads(value) for key, value in cur.iternext()}

    def get_data_types(self):
        ''' Return all data types defined as {object_name}, but without number.
        '''
        num_idx = get_num_length_from_key()

        with LMDBReader._lmdb_cur(self.path) as cur:
            return {key[:-12 - num_idx.send(key)] for key in cur.iternext(values=False)}

    def get_data_by_number(self, t):
        ''' Return data at a specific frame number t
        '''
        num_idx = get_num_length_from_key()

        def check_if_key_equals_t(key):
            try:
                return True if int(key[-12 - num_idx.send(key): -12]) == t else False
            except ValueError:
                return False

        with LMDBReader._lmdb_cur(self.path) as cur:
            keys = (key for key in cur.iternext(values=False) if check_if_key_equals_t(key))
            return {LMDBReader._decode_key(key): pickle.loads(cur.get(key)) for key in keys}

    def get_data_by_type(self, t):
        ''' Return data with key that starts with t
        '''
        with LMDBReader._lmdb_cur(self.path) as cur:
            keys = (key for key in cur.iternext(values=False) if key.startswith(t.encode()))
            return {LMDBReader._decode_key(key): pickle.loads(cur.get(key)) for key in keys}

    def get_params(self):
        ''' Return parameters in a dictionary
        '''
        with LMDBReader._lmdb_cur(self.path) as cur:
            keys = [key for key in cur.iternext(values=False) if key.startswith(b'params_dict')]
            return pickle.loads(cur.get(keys[-1]))

    @staticmethod
    def _decode_key(key):
        ''' Helper method to convert key from byte to str

        Example:
            >>> LMDBReader._decode_key(b'Call0\x80\x03GA\xd7Ky\x06\x9c\xddi.')
            'Call0_1563288602.4510138'

        key: Encoded key. The last 12 bytes are pickled time.time(). 
            The remaining are encoded object name.
        '''

        return f'{key[:-12].decode()}_{pickle.loads(key[-12:])}'

    @staticmethod
    @contextmanager
    def _lmdb_cur(path):
        ''' Helper context manager to open and ensure proper closure of LMDB
        '''

        env = lmdb.open(path)
        txn = env.begin()
        cur = txn.cursor()
        try:
            yield cur

        finally:
            cur.__exit__()
            txn.commit()
            env.close()
