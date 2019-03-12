import time
import os
import h5py
import numpy as np
import asyncio
from nexus.module import Module, Spike
from queue import Empty

import logging; logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Acquirer(Module):
    '''Abstract class for the image acquirer component
       Needs to obtain an image from some input (eg, microscope, file)
       Needs to output frames standardized for processor. Can do some normalization
       Also saves direct to disk in parallel (?)
       Will likely change specifications in the future
    '''
    def getFrame(self):
        # provide function for grabbing the next single frame
        raise NotImplementedError


class FileAcquirer(Acquirer):
    '''Class to import data from files and output
       frames in a buffer, or discrete.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.frame_num = 0
        self.data = None
        self.done = False
        self.flag = False

    def setup(self, filename, *args, **kwargs):
        '''Get file names from config or user input
           Open file stream
           #TODO: implement more than h5 files
        '''
        #super().setup(*args, **kwargs)
        
        if os.path.exists(filename):
            print('Looking for ', filename)
            n, ext = os.path.splitext(filename)[:2]
            if ext == '.h5' or ext == '.hdf5':
                with h5py.File(filename, 'r') as file:
                    keys = list(file.keys())
                    self.data = file[keys[0]].value #only one dset per file atm
                        #frames = np.array(dset).squeeze() #not needed?
                    print('data is ', len(self.data))
        else: raise FileNotFoundError

    def getFrame(self, num):
        ''' Can be live acquistion from disk (?) #TODO
            Here just return frame from loaded data
        '''
        return self.data[num,:,:]

    def run(self):
        ''' Run indefinitely. Calls runAcquirer after checking for singals
        '''
        while True:
            if self.flag:
                try:
                    self.runAcquirer()
                    if self.done:
                        logger.info('Acquirer is done, exiting')
                        return
                except Exception as e:
                    logger.error('Acquirer exception during run: {}'.format(e))
                    break 
            try: 
                signal = self.q_sig.get(timeout=1)
                if signal == Spike.run(): 
                    self.flag = True
                    logger.warning('Received run signal, begin running acquirer')
                elif signal == Spike.quit():
                    logger.warning('Received quit signal, aborting')
                    break
            except Empty as e:
                pass #no signal from Nexus

    def runAcquirer(self):
        '''While frames exist in location specified during setup,
           grab frame, save, put in store
        '''
        if(self.frame_num < len(self.data)):
            id = self.client.put(self.getFrame(self.frame_num), str(self.frame_num))
            try:
                self.q_out.put([{str(self.frame_num):id}])
                self.q_comm.put([self.frame_num])
                self.frame_num += 1
            except Exception as e:
                logger.error('Acquirer general exception: {}'.format(e))

            time.sleep(0.1)

        else: # essentially a done signal from the source (eg, camera)
            logger.error('Done with all available frames: {0}'.format(self.frame_num))
            self.data = None
            self.q_out.put(None)
            self.q_comm.put(None)
            self.done = True

