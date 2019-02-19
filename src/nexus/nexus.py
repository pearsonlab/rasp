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
from acquire.acquire import FileAcquirer
from visual.visual import CaimanVisual, DisplayVisual
from visual.front_end import FrontEnd
from threading import Thread
import asyncio
import concurrent
import functools

import logging; logger = logging.getLogger(__name__)

# TODO: Provide function in abstract classes (?) where Nexus can give/set Links
# This would be for dynamically adding new Links for user-defined modules beyond
# the q_in/q_out and q_comm queues. [Future feature]

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
        #     self.connections.update({connection:q})
        #     self.queues.append(q)
        ''' For each connection:
            create a Link with a name (purpose), start, and end
            Start links to one module's name, end to the other. 
            Nexus gives start_module the Link as a q_in,
              and end_module the Link as a q_out
            Nexus maintains dict of name and associated Link. 
            Nexus also has list of Links that it is itself connected to 
              for communication purposes. 
            OR
            For each connection, create 2 Links. Nexus acts as intermediary. 
        '''

        return tweak

    def createNexus(self):
        self._startStore(1000000000) #default size should be system-dependent
    
        #connect to store and subscribe to notifications
        self.limbo = store.Limbo()
        self.limbo.subscribe()

        self.queues = {}
        self.modules = {} # needed?
        
        # Create connections to the store based on module name
        # Instatiate modules and give them Limbo client connections
        self.tweakLimbo = store.Limbo('tweak')
        self.tweak = self.loadTweak(self.tweakLimbo)

        self.procName = self.tweak.procName
    
        self.visName = self.tweak.visName
        self.visLimbo = store.Limbo(self.visName)
        self.Visual = CaimanVisual(self.visName, self.visLimbo)
        self.modules.update({self.visName:self.Visual}) # needed? TODO

        self.guiName = 'GUI'
        self.GUI = DisplayVisual(self.guiName)
        self.GUI.setVisual(self.Visual)
        self.setupVisual()
        self.queues.update({'gui_comm':Link('gui_comm', self.guiName, self.name)})
        self.GUI.setLink(self.queues['gui_comm'])

        self.runInit() #must be run before import caiman

        self.procLimbo = store.Limbo(self.procName)

        from process.process import CaimanProcessor
        self.Processor = CaimanProcessor(self.procName, self.procLimbo)
        self.ests = None #TODO: this should be Activity as general spike estimates
        self.image = None
        self.A = None
        self.dims = None

        #self.queues.update({'acq_proc':Link('acq_proc'), 'proc_comm':Link('proc_comm')})

        self.acqName = self.tweak.acqName
        self.acqLimbo = store.Limbo(self.acqName)
        self.Acquirer = FileAcquirer(self.acqName, self.acqLimbo)

        self.quitFlag = False
        self.flags = ['run', 'quit']

    def setupProcessor(self):
        '''Setup process parameters
        '''
        self.queues.update({'acq_proc':Link('acq_proc', self.acqName, self.procName), 
                            'proc_comm':Link('proc_comm', self.procName, self.visName)})
        self.Processor = self.Processor.setupProcess(self.queues['acq_proc'], self.queues['proc_vis'], self.queues['proc_comm'])

    def setupAcquirer(self, filename):
        ''' Load data from file
        '''
        self.queues.update({'acq_comm':Link('acq_comm', self.acqName, self.name)})
        self.Acquirer.setupAcquirer(filename, self.queues['acq_proc'], self.queues['acq_comm'])

    def setupVisual(self):
        self.queues.update({'vis_comm':Link('vis_comm', self.visName, self.name),
                            'proc_vis':Link('proc_vis', self.procName, self.visName)})
        self.GUI.visual.setupVisual(self.queues['proc_vis'], self.queues['vis_comm'])

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

    def startNexus(self):
        self.frame = 0

        self.t1 = Process(target=self.runAcquirer)
        #self.t1.daemon = True
        self.t2 = Process(target=self.runProcessor)
        #self.t2.daemon = True

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.pollQueues())

    def run(self):
        print('Starting processes')
        self.t = time.time()

        self.t1.start()
        self.t2.start()

    def quit(self):
        self.t2.join()
        self.t1.join()

        logger.warning('Done with available frames')
        print('total time ', time.time()-self.t)

        self.t3.join()

        self.destroyNexus()

    def runInit(self):
        self.t3 = Process(target=self.GUI.runGUI)
        #self.t3.daemon = True
        self.t3.start()

    async def pollQueues(self):
        gui_fut = None
        acq_fut = None
        proc_fut = None
        polling = [self.queues['gui_comm'], self.queues['acq_comm'], self.queues['proc_comm']]
        tasks = []
        for q in polling:
            tasks.append(asyncio.ensure_future(q.get_async()))

        while True:   

            #print('pending tasks: ',len(tasks))

            done, pending = await asyncio.wait(tasks, return_when=concurrent.futures.FIRST_COMPLETED)
            #TODO: actually kill pending tasks

            if tasks[0] in done or polling[0].status == 'done':
                #r = gui_fut.result()
                r = polling[0].result
                print('GUI signal: ', r)
                self.processGuiSignal(r[0])

                tasks[0] = (asyncio.ensure_future(polling[0].get_async()))

            if tasks[1] in done or polling[1].status == 'done': #catch tasks that complete await wait/gather
                r = polling[1].result
                if r is None:
                    logger.info('Acquirer is finished')
                else:
                    tasks[1] = (asyncio.ensure_future(polling[1].get_async()))

            if tasks[2] in done or polling[2].status == 'done':
                r = polling[2].result
                if r is None:
                    logger.info('Processor is finished')
                    self.quit()
                    break
                else:
                    tasks[2] = (asyncio.ensure_future(polling[0].get_async()))

            self.frame += 1

    def processGuiSignal(self, flag):
        '''Receive flags from the Front End as user input
            List of flags: 0 = run(), 1 = ..
        '''
        print('received signal '+flag)
        if flag in self.flags:
            if flag == self.flags[0]: #start running
                print('running!')
                self.run()
            elif flag == self.flags[1]: #quit
                print('quitting!')
                self.quitFlag = True
                self.quit()
        else:
            logger.error('Signal received from Nexus but cannot identify {}'.format(flag))

    def getTime(self):
        '''TODO: grabe from input source, not processor
        '''
        return self.frame #self.Processor.getTime()

    def getPlotRaw(self, thresh):
        '''Send img to visual to plot
        '''
        # #TMP
        #     # self.getPlotContours()
        #     # #TMP
        #     # (raw, both) = self.Processor.makeImage() #just get denoised frame for now
        #     # #TODO: get some raw data from Acquirer and some contours from Processor
        #     # visRaw = self.Visual.plotRaw(raw)
        #     # (visColor, visBoth) = self.Visual.plotCompFrame(both, thresh)
        #     # return visRaw, visColor, visBoth
        # #data = self.Processor.makeImage() #just get denoised frame for now
        # #TODO: get some raw data from Acquirer and some contours from Processor
        # print('other image ', self.image)
        # visRaw = self.Visual.plotRaw(self.image)
        # print('vis raw frame ', visRaw)
        # return visRaw

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
        loop = asyncio.get_event_loop()
        loop.stop()
        self._closeStore()
        logger.warning('Killed the central store')

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


def Link(name, start, end):
    ''' Abstract constructor for a queue that Nexus uses for
    inter-process/module signaling and information passing

    A Link has an internal queue that can be synchronous (put, get)
    as inherited from multiprocessing.Manager.Queue
    or asynchronous (put_async, get_async) using async executors
    '''

    m = Manager()
    q = AsyncQueue(m.Queue(maxsize=0), name, start, end)
    return q


class AsyncQueue(object):
    def __init__(self,q, name, start, end):
        self.queue = q
        self.real_executor = None
        self.cancelled_join = False

        # Notate what this queue is and from where to where
        # is it passing information
        self.name = name
        self.start = start
        self.end = end
        self.status = 'pending'
        self.result = None

    def getStart(self):
        return self.start
    
    def getEnd(self):
        return self.end

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
        self.status = 'pending'
        try:
            self.result = await loop.run_in_executor(self._executor, self.get)
            #print('got something', self.name)
            self.status = 'done'
            return self.result
        except Exception as e:
            pass
            #print('except ', e)

    def cancel_join_thread(self):
        self._cancelled_join = True
        self._queue.cancel_join_thread()

    def join_thread(self):
        self._queue.join_thread()
        if self._real_executor and not self._cancelled_join:
            self._real_executor.shutdown()


if __name__ == '__main__':
    nexus = Nexus('test')
    nexus.createNexus()
    nexus.setupProcessor()
    cwd = os.getcwd()
    nexus.setupAcquirer(cwd+'/data/Tolias_mesoscope_1.hdf5')
    nexus.startNexus() #start polling, create processes
#    nexus.run()
    nexus.destroyNexus()
    
    
    
    