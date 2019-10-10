import ipaddress
import logging
import time

import h5py
import numpy as np
import zmq

from nexus.actor import Actor, RunManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ZMQAcquirer(Actor):

    def __init__(self, *args, ip=None, port=None, topicfilter=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ip = ip
        self.port = port
        self.topicfilter = topicfilter
        self.frame_num = 0

        # Sanity check
        ipaddress.ip_address(self.ip)  # Check if IP is valid.
        if not 0 <= port <= 65535:
            raise ValueError(f'Port {self.port} invalid.')

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(f"tcp://{self.ip}:{self.port}")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, self.topicfilter)

    def setup(self):
        pass

    def run(self):
        '''Triggered at Run
           Get list of files in the folder and use that as the baseline.
        '''
        self.total_times = []
        self.timestamp = []

        with RunManager(self.name, self.runAcquirer, self.setup, self.q_sig, self.q_comm) as rm:
            print(rm)

        print('Acquire broke, avg time per frame: ', np.mean(self.total_times))
        print('Acquire got through ', self.frame_num, ' frames')
        np.savetxt('timing/acquire_frame_time.txt', self.total_times)
        np.savetxt('timing/acquire_timestamp.txt', self.timestamp)

    def runAcquirer(self):
        ''' Main loop. If there're new files, read and put into store.
        '''
        t = time.time()

        data = self.socket.recv_string()
        self.check_input(data)
        obj_id = self.client.put(data, 'acq_raw' + str(self.frame_num))
        self.q_out.put([{str(self.frame_num): obj_id}])

        self.frame_num += 1
        self.total_times.append(time.time() - t)

    def check_input(self, data):
        pass
