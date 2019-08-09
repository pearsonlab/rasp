import logging
import time

import julia
import numpy as np

from .acquire import Acquirer
from nexus.module import RunManager


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AcquirerMATLAB(Acquirer):
    """
    Class to get image array from MATLAB via Julia.

    """
    def __init__(self, *args, filename='../matlab/test.jl', **kwargs):
        super().__init__(*args, **kwargs)
        self.frame_num = 0
        self.filename = filename
        self.first = True
        self.julia = None
        self.total_times = []

    def setup(self):
        self.julia = julia.Julia(compiled_modules=False)
        self.julia.include(self.filename)

    def run(self):
        with RunManager(self.name, self.run_acquirer, self.setup, self.q_sig, self.q_comm) as rm:
            print(rm)

        print('Acquire broke, avg time per frame: ', np.mean(self.total_times))
        print('Acquire got through ', self.frame_num, ' frames')
        np.savetxt('timing/acquire_frame_time.txt', np.array(self.total_times))
        np.savetxt('timing/acquire_timestamp.txt', np.array(self.timestamp))

    def run_acquirer(self):
        if self.first:
            self.julia.eval('start')()  # Signals MATLAB to start sending data.
            self.first = False

        t = time.time()

        frame = self.julia.eval('get_frame')()
        obj_id = self.client.put(frame, 'acq_raw' + str(self.frame_num))
        self.q_out.put([{str(self.frame_num): obj_id}])
        self.frame_num += 1
        self.total_times.append(time.time() - t)
