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
    def __init__(self, name, client):
        self.name = name
        self.client = client

    def setupAcquirer(self, q_out, q_comm):
        # Essenitally the registration process
        self.q_out = q_out
        self.comm = q_comm

    def run(self):
        # Get images continuously
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

    def setupAcquirer(self, filename, *args, **kwargs):
        '''Get file names from config or user input
           Open file stream
           #TODO: implement more than h5 files
        '''
        super().setupAcquirer(*args, **kwargs)
        
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
        ''' Run indefinitely
        '''
        while True: #TODO: get signal from Link is run vs pause vs stop
            try:
                self.runAcquirer()
                if self.done:
                    logger.info('Acquirer is exiting')
                    return
            except Exception as e:
                logger.error('Acquirer exception during run: {}'.format(e))
                break 

    def runAcquirer(self):
        '''While frames exist in location specified during setup,
           grab frame, save, put in store
        '''
        if(self.frame_num < len(self.data)):
            id = self.client.put(self.getFrame(self.frame_num), str(self.frame_num))
            try:
                self.q_out.put([{str(self.frame_num):id}])
                self.comm.put([self.frame_num])
                self.frame_num += 1
            except Exception as e:
                logger.error('Acquirer general exception: {}'.format(e))

            time.sleep(0.1)

        else: # essentially a done signal from the source (eg, camera)
            logger.error('Done with all available frames: {0}'.format(self.frame_num))
            self.data = None
            self.q_out.put(None)
            self.comm.put(None)
            self.done = True

