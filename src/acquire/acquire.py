import time

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

    def setupAcquirer(self):
        '''Get file names from config or user input
           Open file stream
        '''
        

    def runAcquirer(self):
        '''While frames exist in location specified during setup,
           grab frame, save, put in store
        '''


