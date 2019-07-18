import logging
import pickle
import time
from typing import List

import lmdb
import numpy as np

from .acquire import Acquirer
from nexus.module import RunManager
from utils import utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LMDBAcquirer(Acquirer):
    """ Class to load raw images from previous runs in LMDB format.
    """

    def __init__(self, *args, lmdb_path=None, framerate=30, **kwargs):
        super().__init__(*args, **kwargs)
        self.frame_current = 0
        self.data = None  # Actual loaded data. type: np.ndarray
        self.done = False
        self.flag = False
        self.total_times = []
        self.timestamp = []

        self.lmdb_path = lmdb_path
        self.framerate = 1 / framerate

    def setup(self):

        num_idx = utils.get_num_length_from_key()
        # Get keys associated with raw frames then get objects
        with lmdb.open(self.lmdb_path) as lmdb_env:
            with lmdb_env.begin() as txn:
                with txn.cursor() as cur:
                    keys = cur.iternext(keys=True, values=False)
                    # Need to sort since acquirer store frame nums without leading zeroes.
                    keys_raw = sorted([key for key in keys if key.startswith(b'acq_raw')],
                                      key=lambda key: int(key[-12-num_idx.send(key):-12]))
                    raw_frames = [pickle.loads(cur.get(key)) for key in keys_raw]  # type: List[np.ndarray]

        self.data = np.stack(raw_frames)

    def getFrame(self, num):
        return self.data[num]

    def run(self):
        with RunManager(self.name, self.runAcquirer, self.setup, self.q_sig, self.q_comm) as rm:
            print(rm)

        print('Acquire broke, avg time per frame: ', np.mean(self.total_times))
        print('Acquire got through ', self.frame_current, ' frames')
        np.savetxt('timing/acquire_frame_time.txt', np.array(self.total_times))
        np.savetxt('timing/acquire_timestamp.txt', np.array(self.timestamp))

    def runAcquirer(self):
        t = time.time()

        if self.frame_current < len(self.data):
            frame = self.getFrame(self.frame_current)
            object_id = self.client.put(frame, f'acq_raw{self.frame_current}')

            self.timestamp.append([time.time(), self.frame_current])
            self.q_out.put([{str(self.frame_current): object_id}])
            time.sleep(self.framerate)  # pretend framerate

            self.total_times.append(time.time() - t)
            self.frame_current += 1

        else:
            logger.error(f'Done with all available frames: {self.frame_current}')
            self.done = True
            self.data = None
            self.q_comm.put(None)
