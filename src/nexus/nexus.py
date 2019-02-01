import sys
import time
import subprocess
from multiprocessing import Process, Queue, Manager, cpu_count
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import numpy as np
import pyarrow.plasma as plasma
from nexus import store
from nexus.tweak import Tweak
from process.process import CaimanProcessor
from acquire.acquire import FileAcquirer
from visual.visual import CaimanVisual
from visual.front_end import FrontEnd
from threading import Thread
import asyncio
from PyQt5 import QtGui,QtCore

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
        tweak = Tweak()

        # for connection in tweak.getConnections():
        #     q = Queue()
        #     self.queues.append(q)
        #     self.connections.update({connection:q})

        return tweak

    def createNexus(self):
        self._startStore(1000000000) #default size should be system-dependent
    
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
        self.image = None
        self.coords = None

        self.queue = Link()
        self.queueProc = Link()

        self.acqName = self.tweak.acqName
        self.acqLimbo = store.Limbo(self.acqName)
        self.Acquirer = FileAcquirer(self.acqName, self.acqLimbo)

    def setupProcessor(self):
        '''Setup process parameters
        '''
        self.Processor = self.Processor.setupProcess(self.queue, self.queueProc)

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
                self.getEstimates()
                if self.Processor.done:
                    print('Dropped frames: ', self.Processor.dropped_frames)
                    print('Total number of dropped frames ', len(self.Processor.dropped_frames))
                    return
            except Exception as e:
                logger.exception('What happened: {0}'.format(e))
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
        self.frame = 0
        #self.acq_future = asyncio.ensure_future(self.runAcquirer())  
        #self.proc_future = asyncio.ensure_future(self.runProcessor())  

        #results2 = await asyncio.gather(*[self.proc_future], return_exceptions=True)

        #loop = asyncio.get_event_loop()
        #loop.run_until_complete(self.proc_future)

        self.t1 = Process(target=self.runAcquirer)
        #self.t1.daemon = True

        self.t2 = Process(target=self.runProcessor)
        #self.t2.daemon = True

        self.t1.start()
        self.t2.start()

        app = QtGui.QApplication(sys.argv)
        rasp = FrontEnd()
        rasp.show()
        app.exec_()

        self.t2.join()
        self.t1.join()

        logger.warning('Done with available frames')
        print('total time ', time.time()-t)

    def getEstimates(self):
        '''Get estimates aka neural Activity
        '''
        (self.ests, self.coords, self.image) = self.queueProc.get()
        #print('ests ', self.ests)
        #print('coords ', self.coords)
        print('image', self.image)
        self.frame += 1
        #return self.Processor.getEstimates()
        #return self.limbo.get('outputEstimates')

    def getTime(self):
        '''TODO: grabe from input source, not processor
        '''
        return self.frame #self.Processor.getTime()

    def getPlotEst(self):
        '''Get X,Y to plot estimates from visual
        '''
        #self.getEstimates()
        return self.Visual.plotEstimates(self.ests, self.getTime())

    def getPlotRaw(self):
        '''Send img to visual to plot
        '''
        #data = self.Processor.makeImage() #just get denoised frame for now
        #TODO: get some raw data from Acquirer and some contours from Processor
        print('other image ', self.image)
        visRaw = self.Visual.plotRaw(self.image)
        print('vis raw frame ', visRaw)
        return visRaw

    def getPlotContours(self):
        ''' add neuron shapes to raw plot
        '''
        return self.Visual.plotContours(self.coords)
        #self.Processor.getCoords())

    def getPlotCoM(self):
        return self.Visual.plotCoM(self.coords)

    def selectNeurons(self, x, y):
        ''' Get plot coords, need to translate to neurons
        '''
        self.Visual.selectNeurons(x, y, self.coords)
        return self.Visual.getSelected()

    def destroyNexus(self):
        ''' Method that calls the internal method
            to kill the process running the store (plasma server)
        '''
        #self.t1.kill()
        #self.t2.kill()
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


def Link():
    ''' Abstract constructor for a queue that Nexus uses for
    inter-process/module signaling and information passing

    A Link has an internal queue that can be synchronous (put, get)
    as inherited from multiprocessing.Manager.Queue
    or asynchronous (put_async, get_async) using async executors
    '''

    #def __init__(self, maxsize=0):
    m = Manager()
    q = AsyncQueue(m.Queue(maxsize=0))
    return q


class AsyncQueue(object):
    def __init__(self,q):
        self.queue = q
        self.real_executor = None
        self.cancelled_join = False

    @property
    def _executor(self):
        if not self.real_executor:
            self.real_executor = ThreadPoolExecutor(max_workers=cpu_count())
        return self.real_executor

    def __getstate__(self):
        self_dict = self.__dict__
        self_dict['_real_executor'] = None
        return self_dict

    def __getattr__(self, name):
        if name in ['qsize', 'empty', 'full', 'put', 'put_nowait',
                    'get', 'get_nowait', 'close']:
            return getattr(self.queue, name)
        else:
            raise AttributeError("'%s' object has no attribute '%s'" % 
                                    (self.__class__.__name__, name))

    async def put_async(self, item):
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(self._executor, self.put, item)
        return res

    async def get_async(self):
        loop = asyncio.get_event_loop()
        res  = await loop.run_in_executor(self._executor, self.get)
        return res

    # def cancel_join_thread(self):
    #     self._cancelled_join = True
    #     self._queue.cancel_join_thread()

    # def join_thread(self):
    #     self._queue.join_thread()
    #     if self._real_executor and not self._cancelled_join:
    #         self._real_executor.shutdown()


if __name__ == '__main__':
    nexus = Nexus('test')
    nexus.createNexus()
    nexus.setupProcessor()
    nexus.setupAcquirer('/Users/hawkwings/Documents/Neuro/RASP/rasp/data/Tolias_mesoscope_1.hdf5')
    nexus.run()
    testNexus.destroyNexus()
    
    
    
    