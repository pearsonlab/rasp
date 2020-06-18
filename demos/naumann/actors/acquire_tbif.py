import time
import os
import h5py
import struct
import numpy as np
import random
from pathlib import Path
from skimage.io import imread
from improv.actor import Actor, Spike, RunManager
from queue import Empty
from improv.actors.acquire import FileAcquirer

import logging; logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class TbifAcquirer(FileAcquirer):
    def setup(self):
        if os.path.exists(self.filename):
            print('Looking for ', self.filename)
            _, ext = os.path.splitext(self.filename)[:2]
            if ext == '.tbif':
                self.data = []
                self.stim = []
                self.zpos = []
                with open(self.filename, mode='rb') as f:
                    data = f.read()
                    header = struct.unpack("=IdHHffffdd", data[0:48])
                    #res is: fpp, spf, w, h, 
                    img_size = header[2]*header[3]
                    # -------- repeats here, starts at 48, read 4, 12, img_size
                    for i in range(0,2878):
                        zpos, = struct.unpack("=f", data[48+(16+img_size*2)*i:52+(16+img_size*2)*i])
                        self.zpos.append(zpos)
                        stim = struct.unpack("=fff", data[52+(16+img_size*2)*i:64+(16+img_size*2)*i])
                        self.stim.append(np.asarray(stim))
                        img = struct.unpack("="+str(img_size)+"H", data[64+(16+img_size*2)*i:64+img_size*2+(16+img_size*2)*i])
                        tmp = np.reshape(np.asarray(img, dtype='uint16'), (header[2], header[3]), order='F')
                        self.data.append(tmp.transpose())
                    self.data = np.array(self.data)
            else: 
                logger.error('Cannot load file, bad extension')
                raise Exception
        else: raise FileNotFoundError

    def runAcquirer(self):
        t = time.time()

        if self.done:
            pass 
        elif(self.frame_num < len(self.data)):
            frame = self.getFrame(self.frame_num)
            if self.frame_num == len(self.data):
                print('Done with dataset ', self.frame_num)
            id = self.client.put(frame, 'acq_raw'+str(self.frame_num))
            self.timestamp.append([time.time(), self.frame_num])
            try:
                self.q_out.put([{str(self.frame_num):id}])
                self.links['stim_queue'].put({self.frame_num:self.stim[self.frame_num % len(self.stim)]})
                #logger.info('Current stim: {}'.format(self.stim[self.frame_num]))
                self.frame_num += 1
                # self.saveFrame(frame) # Also log to disk   
            except Exception as e:
                logger.error('Acquirer general exception: {}'.format(e))

            time.sleep(self.framerate) #pretend framerate

        else:
            logger.error('Done with all available frames: {0}'.format(self.frame_num))
            self.data = None
            self.q_comm.put(None)
            self.done = True

        self.total_times.append(time.time()-t)

    def getFrame(self, num):
        ''' Here just return frame from loaded data
        '''
        return self.data[num,30:470,:]