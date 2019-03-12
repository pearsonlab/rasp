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
import signal

import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(filename='logs/nexus_{:%Y%m%d%H%M%S}.log'.format(datetime.now()), 
                    filemode='w', 
                    format='%(asctime)s | %(levelname)-8s | %(name)s | %(lineno)04d | %(message)s')

#fh = logging.FileHandler('logs/nexus_{:%Y%m%d%H%M%S}.log'.format(datetime.now()))
#formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(lineno)04d | %(message)s')
#fh.setFormatter(formatter)
#logger.addHandler(fh)

# TODO: Provide function in abstract classes (?) where Nexus can give/set Links
# This would be for dynamically adding new Links for user-defined modules beyond
# the q_in/q_out and q_comm queues. [Future feature]

# TODO: Set up limbo.notify in async function (?)

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
        self._startStore(2000000000) #default size should be system-dependent
    
        #connect to store and subscribe to notifications
        self.limbo = store.Limbo()
        self.limbo.subscribe()

        self.queues = {}
        self.modules = {} # needed?
        self.flags = {}
        self.processes = []
        
        # Create connections to the store based on module name
        # Instatiate modules and give them Limbo client connections
        self.tweakLimbo = store.Limbo('tweak')
        self.tweak = self.loadTweak() #self.tweakLimbo)

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
        self.t = time.time()

        self.procLimbo = store.Limbo(self.procName)

        from process.process import CaimanProcessor
        self.Processor = CaimanProcessor(self.procName, self.procLimbo)

        self.acqName = self.tweak.acqName
        self.acqLimbo = store.Limbo(self.acqName)
        self.Acquirer = FileAcquirer(self.acqName, self.acqLimbo)

        self.flags.update({'quit':False, 'run':False, 'load':False})

    def setupProcessor(self):
        '''Setup process parameters
        '''
        self.queues.update({'acq_proc':Link('acq_proc', self.acqName, self.procName), 
                            'proc_comm':Link('proc_comm', self.procName, self.name),
                            'proc_signal':Link('proc_signal', self.name, self.procName)})
        self.Processor = self.Processor.setupProcess(self.queues['acq_proc'], self.queues['proc_vis'], self.queues['proc_signal'], self.queues['proc_comm'])

    def setupAcquirer(self, filename):
        ''' Load data from file
        '''
        self.queues.update({'acq_comm':Link('acq_comm', self.acqName, self.name)})
        try:
            self.Acquirer.setupAcquirer(filename, self.queues['acq_proc'], self.queues['acq_comm'])
        except FileNotFoundError:
            logger.error('Dataset not found at {}'.format(filename))

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
        self.Acquirer.run()

    def startNexus(self):
        self.t1 = Process(target=self.runAcquirer)
        self.t1.daemon = True
        self.t2 = Process(target=self.runProcessor)
        self.t2.daemon = True

        loop = asyncio.get_event_loop()

        signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
        for s in signals:
            loop.add_signal_handler(
                s, lambda s=s: asyncio.create_task(stop_polling(s, loop)))

        loop.run_until_complete(self.pollQueues()) #TODO: in Link executor, complete all tasks

    def run(self):
        logger.info('Starting processes')
        self.t = time.time()

        self.processes.extend([self.t1, self.t2])
        
        for t in self.processes:
            t.start()

        self.queues['proc_signal'].put('run')

    def quit(self):
        logger.warning('Killing child processes')
        
        self.processes.append(self.t3)
        for t in self.processes:
            if t.is_alive():
                t.terminate()
            t.join()

        logger.warning('Done with available frames')
        print('total time ', time.time()-self.t)

        self.destroyNexus()

    def runInit(self):
        self.t3 = Process(target=self.GUI.runGUI)
        self.t3.daemon = True
        self.t3.start()
        logger.info('Started Front End')

    async def pollQueues(self):
        gui_fut = None
        acq_fut = None
        proc_fut = None
        polling = [self.queues['gui_comm'], self.queues['acq_comm'], self.queues['proc_comm']]
        tasks = []
        for q in polling:
            tasks.append(asyncio.ensure_future(q.get_async()))

        while not self.flags['quit']:   

            #print('pending tasks: ',len(tasks))

            done, pending = await asyncio.wait(tasks, return_when=concurrent.futures.FIRST_COMPLETED)
            #TODO: actually kill pending tasks
            #TODO: tasks as dict vs list indexing so we can associate a task with the module/Link

            if tasks[0] in done or polling[0].status == 'done':
                #r = gui_fut.result()
                r = polling[0].result
                self.processGuiSignal(r)

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

        logger.warning('Shutting down polling')

    def processGuiSignal(self, flag):
        '''Receive flags from the Front End as user input
            List of flags: 0 = run(), 1 = quit, 2 = load tweak
        '''
        logger.info('Received signal from GUI: '+flag[0])
        if flag[0] in self.flags.keys():
            if flag[0] == 'run':
                logger.info('Begin run!')
                self.flags['run'] = True
                self.run()
            elif flag[0] == 'quit':
                logger.warning('Quitting the program!')
                self.flags['quit'] = True
                self.quit()
            elif flag[0] == 'load':
                logger.info('Loading Tweak config from file '+flag[1])
                self.loadTweak(flag[1])
        else:
            logger.error('Signal received from Nexus but cannot identify {}'.format(flag))

    def destroyNexus(self):
        ''' Method that calls the internal method
            to kill the process running the store (plasma server)
        '''
        logger.warning('Destroying Nexus')
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

    async def stop_polling(signal, loop):
        logging.info(f'Received exit signal {signal.name}...')
        
        tasks = [t for t in asyncio.all_tasks() if t is not
                asyncio.current_task()]

        [task.cancel() for task in tasks]

        logging.info('Canceling outstanding tasks')
        await asyncio.gather(*tasks)
        loop.stop()
        logging.info('Shutdown complete.')
    

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
            logger.debug('Link '+self.name+' received input: '+self.result)
            self.status = 'done'
            return self.result
        except Exception as e:
            pass #TODO
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
#    nexus.destroyNexus()
    #os._exit(0)
    
    
    