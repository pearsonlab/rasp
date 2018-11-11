import sys
sys.path.append('../')
import time
import subprocess
from multiprocessing import Pool
import numpy as np
import pyarrow as arrow
import pyarrow.plasma as plasma
from nexus import store
from nexus.tweak import Tweak
from visual import Visual
from process.process import Processor
from acquire.acquire import Acquirer

import logging; logger = logging.getLogger(__name__)

class Nexus():
    ''' Main server class for handling objects in RASP
    
    '''

    def __init__(self, name):
        self.name = name


    def __str__(self):
        return self.name
    

    def loadTweak(self, file=None):
        #TODO load from file or user input?
        return Tweak(file)


    def createNexus(self):
        self._startStore(100000) #TODO
    
        self.limbo = store.Limbo()
        
        # Create connections to the store based on module name
        # Instatiate modules and give them Limbo client connections
        self.tweakLimbo = store.Limbo('tweak')
        self.tweak = self.loadTweak(self.tweakLimbo)
    
        self.visName = seal.tweak.visName
        self.visLimbo = store.Limbo(self.visName)
        self.Visual = Visual(self.visName, self.visLimbo)

        self.procName = self.tweak.procName
        self.procLimbo = store.Limbo(self.procName)
        self.Processor = Processor(self.procName, self.procLimbo)

        self.acqName = self.tweak.acqName
        self.acqLimbo = store.Limbo(self.acqName)
        self.Acquirer = Acquirer(self.acqName, self.acqLimbo)


    def destroyNexus(self):
        self._closeStore()
    

    def _closeStore(self):
        try:
            self.p.kill()
            logger.info('Store closed successfully')
        except Exception as e:
            logger.exception('Cannot close store {0}'.format(e))


    def _startStore(self, size):
        ''' Start a subprocess that runs the plasma store
            Raises a RuntimeError exception size is undefined
            Raises an Exception if the plasma store doesn't start
        '''
        
        if size is None:
            raise RuntimeEror('Server size needs to be specified')
        try:
            self.p = subprocess.Popen(['plasma_store',
                              '-s', '/tmp/store',
                              '-m', str(size)],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
            logger.info('Store started successfully')
        except Exception as e:
            logger.exception('Store cannot be started: {0}'.format(e))


if __name__ == '__main__':
    testNexus = Nexus('test')
    testNexus.createNexus()
    
    testNexus.destroyNexus()
    
    
    
    