"""
Utilities to read LMDB

"""

import numbers
import os
import pickle
from contextlib import contextmanager
from typing import Dict, Set

import lmdb


class LMDBReader:
    def __init__(self, path):
        """
        Constructor for the LMDB reader.

        :param path: Path to LMDB folder
        :type path: str

        """
        if not os.path.exists(path):
            raise FileNotFoundError
        self.path = path

    def get_all_data(self):
        """
        Load all data from LMDB into a dictionary.
        Make sure that the LMDB is small enough to fit in RAM.

        :return: All data in a dictionary.
        :rtype: Dict[str: object]
        """

        with LMDBReader._lmdb_cur(self.path) as cur:
            return {LMDBReader._decode_key(key): pickle.loads(value) for key, value in cur.iternext()}

    def get_data_types(self):
        """
        :return: A set of all data types defined as {object_name} without number when the data were put into Limbo.
        :rtype: Set[str]
        """
        max_num_len = 1  # Keep track of largest digit for performance.

        # Assuming that object name does not have any digits.
        def get_name_from_key(key):
            nonlocal max_num_len
            name_num = key[:-12].decode()

            if not name_num[-max_num_len:].isdigit():
                i = max_num_len
                while not name_num[-i:].isdigit():
                    if i < 0:
                        return name_num
                    i -= 1
                return name_num[:-i]

            while name_num[-(max_num_len + 1):].isdigit():
                max_num_len += 1
            return name_num[:-max_num_len]

        with LMDBReader._lmdb_cur(self.path) as cur:
            return {get_name_from_key(key) for key in cur.iternext(values=False)}

    def get_data_by_number(self, t):
        """
        Return data at a specific frame number

        :param t: Frame number
        :type t: int
        :return:
        :rtype: Dict[str: object]
        """
        if not isinstance(t, numbers.Integral):
            raise TypeError

        max_num_len = 1  # Keep track of largest digit for performance.

        # Assuming that object name does not have any digits.
        def get_num_from_key(key):
            nonlocal max_num_len
            name_num = key[:-12].decode()

            if not name_num[-max_num_len:].isdigit():
                i = max_num_len
                while not name_num[-i:].isdigit():
                    if i < 0:
                        return -1
                    i -= 1
                return name_num[-i:]

            while name_num[-(max_num_len + 1):].isdigit():
                max_num_len += 1
            return name_num[-max_num_len:]

        with LMDBReader._lmdb_cur(self.path) as cur:
            keys = (key for key in cur.iternext(values=False) if int(get_num_from_key(key)) == t)
            return {LMDBReader._decode_key(key): pickle.loads(cur.get(key)) for key in keys}

    def get_data_by_type(self, t):
        """
        Return data with key that starts with {t}

        :param t: Data prefix
        :type t: str
        :return:
        :rtype: Dict[str: object]
        """

        with LMDBReader._lmdb_cur(self.path) as cur:
            keys = (key for key in cur.iternext(values=False) if key.startswith(t.encode()))
            return {LMDBReader._decode_key(key): pickle.loads(cur.get(key)) for key in keys}

    @staticmethod
    def _decode_key(key):
        """
        Helper method to convert key from byte to str

        Example:
            >>> LMDBReader._decode_key(b'Call0\x80\x03GA\xd7Ky\x06\x9c\xddi.')
            'Call0_1563288602.4510138'

        :param key: Encoded key. The last 12 bytes are pickled time.time(). The remaining are encoded object name.
        :type key: byte
        :return: Decoded key
        :rtype str
        """

        return f'{key[:-12].decode()}_{pickle.loads(key[-12:])}'

    @staticmethod
    @contextmanager
    def _lmdb_cur(path):
        """ Helper context manager to open and ensure proper closure of LMDB. """

        env = lmdb.open(path)
        txn = env.begin()
        cur = txn.cursor()
        try:
            yield cur

        finally:
            cur.__exit__()
            txn.commit()
            env.close()
