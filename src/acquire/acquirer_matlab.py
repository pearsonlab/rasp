import logging
import time
from functools import partial

import matlab.engine
import numpy as np

from .acquire import Acquirer
from nexus.module import RunManager


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AcquirerMATLAB(Acquirer):
    """
    Class to get image array from MATLAB.

    This class starts a MATLAB engine and loads the memory-mapped file(s).

    It checks the marker for a new image in MATLAB and transfer that new image into a np.ndarray.

    """
    def __init__(self, path_mmap='../matlab/scanbox.mmap', path_header='../matlab/header.mmap',
                 img_dim=None, img_dtype='int16', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.path_mmap = path_mmap
        self.path_header = path_header
        self.img_dim = [440, 256] if img_dim is None else img_dim
        self.img_dtype = img_dtype
        self.frame_num = 0
        self.total_times = []
        self.first = True

        self.eng = None
        self.mlassign = None

    def setup(self):
        self.eng = matlab.engine.start_matlab()
        self.mlassign = partial(self.eng.eval, nargout=0)  # MATLAB code that does has no return must be run using this.
        self.mlassign(
            f"img = memmapfile('{self.path_mmap}', 'Format', {{'{self.img_dtype}', {self.img_dim}, 'data'}});")
        self.mlassign(
            f"header = memmapfile('{self.path_header}', 'Format', 'int16', 'Writable', true);")

    def run(self):
        with RunManager(self.name, self.run_acquirer, self.setup, self.q_sig, self.q_comm) as rm:
            print(rm)

        print('Acquire broke, avg time per frame: ', np.mean(self.total_times))
        print('Acquire got through ', self.frame_num, ' frames')
        np.savetxt('timing/acquire_frame_time.txt', np.array(self.total_times))
        np.savetxt('timing/acquire_timestamp.txt', np.array(self.timestamp))

    def run_acquirer(self):
        if self.first:
            self.mlassign("header.Data(2) = 1")  # Start data generation
            self.first = False

        t = time.time()

        # Block until new image arrives.
        self.mlassign(
            """
            while true
                if header.Data(1) == 1
                    break;
                end
            end
            header.Data(1) = 0;
            """)

        raw = self.eng.eval('img.Data.data;')  # matlab.mlarray.int16
        frame = np.array(raw._data).reshape(raw.size[::-1]).T  # To keep conversion fast

        obj_id = self.client.put(frame, 'acq_raw' + str(self.frame_num))
        self.q_out.put([{str(self.frame_num): obj_id}])
        self.frame_num += 1
        self.total_times.append(time.time() - t)
