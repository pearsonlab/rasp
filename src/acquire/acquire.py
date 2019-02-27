import time
import os
import h5py
import numpy as np
import asyncio
import logging; logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Acquirer():
    '''Abstract class for the image acquirer component
       Needs to obtain an image from some input (eg, microscope, file)
       Needs to output frames standardized for processor. Can do some normalization
       Also saves direct to disk in parallel (?)
       Will likely change specifications in the future
    '''
    def setupAcquirer(self):
        # Essenitally the registration process
        raise NotImplementedError

    def runAcquirer(self):
        # Get images continuously
        raise NotImplementedError


class FileAcquirer(Acquirer):
    '''Class to import data from files and output
       frames in a buffer, or discrete.
    '''
    
    def __init__(self, name, client):
        self.name = name
        self.client = client
        self.frame_num = 0
        self.data = None

    def setupAcquirer(self, filename, q_out, q_comm):
        '''Get file names from config or user input
           Open file stream
           #TODO: implement more than h5 files
        '''
        self.q_out = q_out
        self.comm = q_comm
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

    def runAcquirer(self):
        '''While frames exist in location specified during setup,
           grab frame, save, put in store
        '''
        if(self.frame_num < len(self.data)):
            #id = self.client.replace(self.getFrame(self.frame_num), 'curr_frame')
            id = self.client.put(self.getFrame(self.frame_num), str(self.frame_num))
            try:
                self.q_out.put([{str(self.frame_num):id}])
                self.comm.put([self.frame_num])
                self.frame_num += 1
            except Exception as e:
                logger.error('AAAA: {}'.format(e))

            time.sleep(0.1)
        else:
            logger.error('Done with all available frames: {0}'.format(self.frame_num))
            #self.client.delete('curr_frame')
            self.data = None
            self.q_out.put(None)
            self.comm.put(None)

