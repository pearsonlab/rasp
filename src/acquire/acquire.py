import time
import os
import h5py
import numpy as np
import logging; logger = logging.getLogger(__name__)

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

    def setupAcquirer(self, filename):
        '''Get file names from config or user input
           Open file stream
           #TODO: implement more than h5 files
        '''
        if os.path.exists(filename):
            n, ext = os.path.splitext(filename)[:2]
            if ext == '.h5' or ext == '.hdf5':
                with h5py.File(filename, 'r') as file:
                    keys = list(file.keys())
                    self.data = file[keys[0]].value #only one dset per file atm
                        #frames = np.array(dset).squeeze() #not needed?
                    #print(self.data[0,:,:].shape)

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
            id = self.client.put(self.getFrame(self.frame_num), 'curr_frame')
            self.frame_num += 1
        else:
            logger.error('Done with all available frames')

