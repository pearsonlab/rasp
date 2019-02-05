import sys
import os
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
        self.A = None
        self.dims = None

        self.queues = {}
        #self.queues.update({'acq_proc':Link('acq_proc'), 'proc_comm':Link('proc_comm')})

        self.acqName = self.tweak.acqName
        self.acqLimbo = store.Limbo(self.acqName)
        self.Acquirer = FileAcquirer(self.acqName, self.acqLimbo)

    def setupProcessor(self):
        '''Setup process parameters
        '''
        self.queues.update({'acq_proc':Link('acq_proc'), 'proc_comm':Link('proc_comm')})
        self.Processor = self.Processor.setupProcess(self.queues['acq_proc'], self.queues['proc_comm'])

    def setupAcquirer(self, filename):
        ''' Load data from file
        '''
        self.queues.update({'acq_comm':Link('acq_comm')})
        self.Acquirer.setupAcquirer(filename, self.queues['acq_proc'], self.queues['acq_comm'])

    def runProcessor(self):
        '''Run the processor continually on input frames
        '''
        self.Processor.run()

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

        #self.poll_future = asyncio.ensure_future(self.pollQueues)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.pollQueues())

        # app = QtGui.QApplication(sys.argv)
        # rasp = FrontEnd()
        # rasp.show()
        # app.exec_()

        self.t2.join()
        self.t1.join()

        logger.warning('Done with available frames')
        print('total time ', time.time()-t)

    async def pollQueues(self):
        while True:
            acq_comm = await self.queues['acq_comm'].get_async()
            if acq_comm is None:
                logger.error('Acquirer is finished')
            proc_comm = await self.queues['proc_comm'].get_async()
            if proc_comm is not None:
                (self.ests, self.A, self.dims, self.image) = proc_comm
                #print('image', self.image)
            else:
                logger.error('Processor is finished')
                break
            await asyncio.sleep(0.01)
            self.frame += 1

    def getEstimates(self):
        '''Get estimates aka neural Activity
        '''
        (self.ests, self.A, self.dims, self.image) = self.queues['proc_comm'].get()
        #print('ests ', self.ests)
        #print('coords ', self.coords)
        #print('image', self.image)
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
        return self.Visual.plotContours(self.A, self.dims)
        #self.Processor.getCoords())

    def getPlotCoM(self):
        return self.Visual.plotCoM(self.A, self.dims)

    def selectNeurons(self, x, y):
        ''' Get plot coords, need to translate to neurons
        '''
        self.Visual.selectNeurons(x, y, self.A, self.dims)
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


def Link(name):
    ''' Abstract constructor for a queue that Nexus uses for
    inter-process/module signaling and information passing

    A Link has an internal queue that can be synchronous (put, get)
    as inherited from multiprocessing.Manager.Queue
    or asynchronous (put_async, get_async) using async executors
    '''

    #def __init__(self, maxsize=0):
    m = Manager()
    q = AsyncQueue(m.Queue(maxsize=0), name)
    return q


class AsyncQueue(object):
    def __init__(self,q, name):
        self.queue = q
        self.real_executor = None
        self.cancelled_join = False
        self.name = name

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
    cwd = os.getcwd()
    nexus.setupAcquirer(cwd+'/data/Tolias_mesoscope_1.hdf5')
    nexus.run()
    nexus.destroyNexus()
    
    
    
    