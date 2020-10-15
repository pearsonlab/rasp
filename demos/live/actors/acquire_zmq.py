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
from improv.actor import Actor, Spike, RunManager
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
        self.framesendtimes = []
        self.stimsendtimes = []
        self.tailsendtimes = []
        self.tails = []

        with RunManager(self.name, self.runAcquirer, self.setup, self.q_sig, self.q_comm) as rm:
            print(rm)
        print('-------------------------------------------- HERE')

        self.imgs = np.array(self.saveArray)
        f = h5py.File('output/sample_stream.h5', 'w', libver='latest')
        f.create_dataset("default", data=self.imgs)
        f.close()

        np.savetxt('output/stimmed.txt', np.array(self.stimmed))
        np.savetxt('output/tails.txt', np.array(self.tails))
        np.savetxt('output/timing/frametimes.txt', np.array(self.frametimes))
        np.savetxt('output/timing/framesendtimes.txt', np.array(self.framesendtimes), fmt="%s")
        np.savetxt('output/timing/stimsendtimes.txt', np.array(self.stimsendtimes), fmt="%s")
        np.savetxt('output/timing/tailsendtimes.txt', np.array(self.tailsendtimes), fmt="%s")

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
            # logger.info(msg_parts[0].split(b' ')[:4])
            tag = msg_parts[0].split(b' ')[0]
            # sendtime = msg_parts[0].split(b' ')[1].decode()

            if tag == b'stimid':
                msg_parts = [part.strip() for part in msg.split(b' ')]
                # print(msg_parts)
                sendtime = msg_parts[2].decode()
                angle = int(msg_parts[7].decode()[:-1])
                vel = float(msg_parts[9].decode()[:-1])
                # print('stim sendtime ', sendtime)
                # print('stimulus id: {}, {}'.format(angle, vel))

                # output example: stimulus id: b'background_stim'

                #calibration check:
                angle = 270+angle
                if angle>360:
                    angle-=360

                stim = 0
                # stimonOff = 20
                if np.abs(vel) > 0:
                    stimonOff = 20
                else:
                    stimonOff = 0

                # if msg_parts[1] == b'Left':
                #     stim = 4
                # elif msg_parts[1] == b'Right':
                #     stim = 3
                # elif msg_parts[1] == b'forward':
                #     stim = 9
                # elif msg_parts[1] == b'backward':
                #     stim = 13
                # elif msg_parts[1] == b'background_stim':
                #     stimonOff = 0
                #     print('Stim off')
                # elif msg_parts[1] == b'Left_Backward':
                #     stim = 14
                # elif msg_parts[1] == b'Right_Backward':
                #     stim = 12
                # elif msg_parts[1] == b'Left_Forward':
                #     stim = 16
                # elif msg_parts[1] == b'Right_Forward':
                #     stim = 10

                if angle == 0:
                    stim = 9
                elif angle == 90:
                    stim = 3
                elif angle == 180:
                    stim = 13
                elif angle == 270:
                    stim = 4
                elif angle == 45:
                    stim = 10
                elif angle == 135:
                    stim = 12
                elif angle == 225:
                    stim = 14
                elif angle == 315:
                    stim = 16
                else:
                    logger.error('Stimulus unrecognized')

                logger.info('Stimulus: {}'.format(stim))
                

                self.links['stim_queue'].put({self.frame_num:[stim, stimonOff]})
                self.stimmed.append([self.frame_num, stim, time.time()])
                self.stimsendtimes.append([sendtime])

            elif tag == b'frame':
                t0 = time.time()
                sendtime =  msg_parts[0].split(b' ')[2].decode()
                # print(sendtime)
                array = np.array(json.loads(msg_parts[1]))  # assuming the following message structure: 'tag: message'
                # print('frame ', self.frame_num)
                # print('{}'.format(msg_parts[0])) # messsage length: {}. Element sum: {}; time to process: {}'.format(msg_parts[0], len(msg),
                                                                                            # array.sum(), time.time() - t0))
                # output example: b'frame ch0 10:02:01.115 AM 10/11/2019' messsage length: 1049637. Element sum: 48891125; time to process: 0.04192757606506348
                
                obj_id = self.client.put(array, 'acq_raw' + str(self.frame_num))
                self.q_out.put([{str(self.frame_num): obj_id}])

                self.saveArray.append(array)
                self.frametimes.append([self.frame_num, time.time()])
                self.framesendtimes.append([sendtime])

                self.frame_num += 1
                self.total_times.append(time.time() - t0)

            elif tag == b'tail':
                t0 = time.time()
                sendtime = msg_parts[0].split(b' ')[1].decode()
                msg = msg_parts[0].split(b' ')[4:]
                # print(msg)
                vlist = []
                for i,m in enumerate(msg):
                    try:
                        v = int(m.decode())
                    except ValueError:
                        v = int(m.decode()[:-1])
                    vlist.append(v)
                self.tails.append(np.array(vlist))
                self.tailsendtimes.append([sendtime])

            else:
                if len(msg) < 100:
                    print(msg)
                else:
                    print('msg length: {}'.format(len(msg)))

        except zmq.Again as e:
            pass #no messages available
        except Exception as e:
            print('error: {}'.format(e))