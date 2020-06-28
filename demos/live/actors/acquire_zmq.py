import time
import os
import h5py
import struct
import numpy as np
import random
import ipaddress
import zmq
import json
from pathlib import Path
from skimage.external.tifffile import imread
from nexus.actor import Actor, Spike, RunManager
from queue import Empty

import logging; logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ZMQAcquirer(Actor):

    def __init__(self, *args, ip=None, ports=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ip = ip
        self.ports = ports
        self.frame_num = 0

        # Sanity check
        # ipaddress.ip_address(self.ip)  # Check if IP is valid.
        # if not 0 <= port <= 65535:
        #     raise ValueError(f'Port {self.port} invalid.')

        # self.context = zmq.Context()
        # self.socket = self.context.socket(zmq.SUB)
        # self.socket.connect(f"tcp://{self.ip}:{self.port}")
        # self.socket.setsockopt_string(zmq.SUBSCRIBE, self.topicfilter)

    def setup(self):
        context = zmq.Context()
        self.socket = context.socket(zmq.SUB)
        for port in self.ports:
            self.socket.connect("tcp://"+str(self.ip)+":"+str(port))
        self.socket.setsockopt(zmq.SUBSCRIBE, b'')

        self.saveArray = []

        ## TODO: save initial set of frames to data/init_stream.h5

    def run(self):
        '''Triggered at Run
        '''
        self.total_times = []
        self.timestamp = []
        self.stimmed = []
        self.frametimes = []

        with RunManager(self.name, self.runAcquirer, self.setup, self.q_sig, self.q_comm) as rm:
            print(rm)

        self.imgs = np.array(self.saveArray)
        f = h5py.File('output/sample_stream.h5', 'w', libver='latest')
        f.create_dataset("default", data=self.imgs)
        f.close()

        np.savetxt('output/stimmed.txt', np.array(self.stimmed))
        np.savetxt('output/timing/frametimes.txt', np.array(self.frametimes))

        print('Acquisition complete, avg time per frame: ', np.mean(self.total_times))
        print('Acquire got through ', self.frame_num, ' frames')
        np.savetxt('output/timing/acquire_frame_time.txt', self.total_times)
        np.savetxt('output/timing/acquire_timestamp.txt', self.timestamp)

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

                stim = 0
                stimonOff = 20

                if msg_parts[1] == b'Left':
                    stim = 4
                elif msg_parts[1] == b'Right':
                    stim = 3
                elif msg_parts[1] == b'forward':
                    stim = 9
                elif msg_parts[1] == b'backward':
                    stim = 13
                elif msg_parts[1] == b'background_stim':
                    stimonOff = 0
                    print('Stim off')
                elif msg_parts[1] == b'Left_Backward':
                    stim = 14
                elif msg_parts[1] == b'Right_Backward':
                    stim = 12
                elif msg_parts[1] == b'Left_Forward':
                    stim = 16
                elif msg_parts[1] == b'Right_Forward':
                    stim = 10

                self.links['stim_queue'].put({self.frame_num:[stim, stimonOff]})
                self.stimmed.append([self.frame_num, stim, time.time()])

            elif tag == b'frame':
                t0 = time.time()
                array = np.array(json.loads(msg_parts[1]))  # assuming the following message structure: 'tag: message'
                # print('frame ', self.frame_num)
                # print('{}'.format(msg_parts[0])) # messsage length: {}. Element sum: {}; time to process: {}'.format(msg_parts[0], len(msg),
                                                                                            # array.sum(), time.time() - t0))
                # output example: b'frame ch0 10:02:01.115 AM 10/11/2019' messsage length: 1049637. Element sum: 48891125; time to process: 0.04192757606506348
                
                obj_id = self.client.put(array, 'acq_raw' + str(self.frame_num))
                self.q_out.put([{str(self.frame_num): obj_id}])

                self.saveArray.append(array)
                self.frametimes.append([self.frame_num, time.time()])

                self.frame_num += 1
                self.total_times.append(time.time() - t0)

            else:
                if len(msg) < 100:
                    print(msg)
                else:
                    print('msg length: {}'.format(len(msg)))

        except zmq.Again as e:
            pass #no messages available
        except Exception as e:
            print('error: {}'.format(e))