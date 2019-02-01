import sys
import time
import subprocess
from multiprocessing import Process, Queue
from threading import Thread
import numpy as np
import pyarrow as arrow
import pyarrow.plasma as plasma
from nexus import store
from nexus.tweak import Tweak
from process.process import CaimanProcessor
from acquire.acquire import FileAcquirer
from visual.visual import CaimanVisual

import logging; logger = logging.getLogger(__name__)

class Nexus():
    ''' Main server class for handling objects in RASP
    '''
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name
    
    def loadTweak(self, file=None):
        #TODO load from file or user input
        return Tweak(file)

    def createNexus(self):
        self._startStore(100000000) #default size should be system-dependent
    
        #connect to store and subscribe to notifications
        self.limbo = store.Limbo()
        self.limbo.subscribe()
        
        # Create connections to the store based on module name
        # Instatiate modules and give them Limbo client connections
        self.tweakLimbo = store.Limbo('tweak')
        self.tweak = self.loadTweak(self.tweakLimbo)
    
        self.visName = self.tweak.visName
        self.visLimbo = store.Limbo(self.visName)
        self.Visual = CaimanVisual(self.visName, self.visLimbo)

        self.procName = self.tweak.procName
        self.procLimbo = store.Limbo(self.procName)
        self.Processor = CaimanProcessor(self.procName, self.procLimbo)
        self.ests = None #TODO: this should be Activity as general spike estimates
        self.queue = Queue()

        self.acqName = self.tweak.acqName
        self.acqLimbo = store.Limbo(self.acqName)
        self.Acquirer = FileAcquirer(self.acqName, self.acqLimbo)

    def setupProcessor(self):
        '''Setup process parameters
        '''
        self.Processor = self.Processor.setupProcess(self.queue)

    def setupAcquirer(self, filename):
        ''' Load data from file
        '''
        self.Acquirer.setupAcquirer(filename, self.queue)

    def runProcessor(self):
        '''Run the processor continually on input frames
        '''
        while True:
        #self.Processor.client.reset() #Reset client to limbo...FIXME
        #t = time.time()
            try: 
            #frame_loc = self.Acquirer.client.getStored()['curr_frame']
            #self.Processor.client.updateStored('frame', frame_loc)
                self.Processor.runProcess()
            except Exception as e:
                logger.warning('No available frames for processing: {0}'.format(e))
                break
        
        #frames = self.Processor.getTime()
        #print('time for ', frames, ' frames is ', time.time()-t, ' s')
        #logger.warning('Done running process')

    def runAcquirer(self):
        ''' Run the acquirer continually 
        '''
        while True:
            self.Acquirer.runAcquirer()
            if self.Acquirer.data is None:
                break

    def run(self):
        t=time.time()
        #while True:
        #    self.runAcquirer()
        #    if self.Acquirer.data is not None:
        #        self.runProcessor()
        #    else:
        #        logger.warning('No more data')
        #        break
        self.t1 = Thread(target=self.runAcquirer)
        self.t1.daemon = True
        #self.t.start()        
        self.t2 = Thread(target=self.runProcessor)
        self.t2.daemon = True

        self.t1.start()
        self.t2.start()

        self.t2.join()
        self.t1.join()

        logger.warning('Done with available frames')
        print('total time ', time.time()-t)

    def getEstimates(self):
        '''Get estimates aka neural Activity
        '''
        return self.Processor.getEstimates()

    def getTime(self):
        '''TODO: grabe from input source, not processor
        '''
        return self.Processor.getTime()

    def getPlotEst(self):
        '''Get X,Y to plot estimates from visual
        '''
        return self.Visual.plotEstimates(self.getEstimates(), self.getTime())

    def getPlotRaw(self):
        '''Send img to visual to plot
        '''
        data = self.Processor.makeImage() #just get denoised frame for now
        #TODO: get some raw data from Acquirer and some contours from Processor
        visRaw = self.Visual.plotRaw(data)
        return visRaw

    def getPlotContours(self):
        ''' add neuron shapes to raw plot
        '''
        return self.Visual.plotContours(self.Processor.getCoords())

    def getPlotCoM(self):
        return self.Visual.plotCoM(self.Processor.getCoords())

    def selectNeurons(self, x, y):
        ''' Get plot coords, need to translate to neurons
        '''
        self.Visual.selectNeurons(x, y, self.Processor.getCoords())
        return self.Visual.getSelected()

    def destroyNexus(self):
        ''' Method that calls the internal method
            to kill the process running the store (plasma server)
        '''
        self._closeStore()

    def _closeStore(self):
        ''' Internal method to kill the subprocess
            running the store (plasma sever)
        '''
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
            raise RuntimeError('Server size needs to be specified')
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
    
    
    
    