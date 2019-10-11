import ipaddress
import logging
import time

import h5py
import numpy as np
import zmq
import json

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

        # self.context = zmq.Context()
        # self.socket = self.context.socket(zmq.SUB)
        # self.socket.connect(f"tcp://{self.ip}:{self.port}")
        # self.socket.setsockopt_string(zmq.SUBSCRIBE, self.topicfilter)

    def setup(self):
        context = zmq.Context()
        self.socket = context.socket(zmq.SUB)
        self.socket.connect("tcp://10.122.170.21:4701")
        self.socket.connect("tcp://10.122.170.21:4702")
        self.socket.setsockopt(zmq.SUBSCRIBE, b'')

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
        #TODO: use poller instead to prevent blocking, include a timeout
        try:
            msg = self.socket.recv(flags=zmq.NOBLOCK)
            msg_parts = [part.strip() for part in msg.split(b': ', 1)]
            tag = msg_parts[0].split(b' ')[0]

            if tag == b'stimid':
                print('stimulus id: {}'.format(msg_parts[1]))
                # output example: stimulus id: b'background_stim'

                self.links['stim_queue'].put({self.frame_num:msg_parts[1]}) #TODO: stimID needs to be numbered?

            elif tag == b'frame':
                t0 = time.time()
                array = np.array(json.loads(msg_parts[1]))  # assuming the following message structure: 'tag: message'
                print('{} messsage length: {}. Element sum: {}; time to process: {}'.format(msg_parts[0], len(msg),
                                                                                            array.sum(), time.time() - t0))
                # output example: b'frame ch0 10:02:01.115 AM 10/11/2019' messsage length: 1049637. Element sum: 48891125; time to process: 0.04192757606506348
                
                obj_id = self.client.put(array, 'acq_raw' + str(self.frame_num))
                self.q_out.put([{str(self.frame_num): obj_id}])

                self.frame_num += 1
                self.total_times.append(time.time() - t)

            else:
                if len(msg) < 100:
                    print(msg)
                else:
                    print('msg length: {}'.format(len(msg)))

        except zmq.Again as e:
            pass #no messages available
        except Exception as e:
            print('error: {}'.format(e))
