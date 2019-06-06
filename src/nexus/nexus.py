import sys
import os
import time
import subprocess
from multiprocessing import Process, Queue, Manager, cpu_count
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import numpy as np
from PyQt5 import QtGui, QtWidgets
import pyarrow.plasma as plasma
from importlib import import_module
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
from nexus.module import Spike
from queue import Empty, Full

#import nest_asyncio
#nest_asyncio.apply()

import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO,
                    format='%(name)s %(message)s',
                    handlers=[logging.FileHandler("example2.log"),
                              logging.StreamHandler()])
#logging.basicConfig(filename='logs/nexus_{:%Y%m%d%H%M%S}.log'.format(datetime.now()), 
                   #filemode='w', 
                  #format='%(asctime)s | %(levelname)-8s | %(name)s | %(lineno)04d | %(message)s')

        #fh = logging.FileHandler('logs/nexus_{:%Y%m%d%H%M%S}.log'.format(datetime.now()))
        #formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(lineno)04d | %(message)s')
        #fh.setFormatter(formatter)
        #logger.addHandler(fh)

# TODO: Set up limbo.notify in async function (?)

class Nexus():
    ''' Main server class for handling objects in RASP
    '''
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name
    
    def loadTweak(self, file=None):
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
        #TODO load from file or user input, as in dialogue through FrontEnd?

        self.tweak = Tweak(file)
        self.tweak.createConfig()

        # create all data links requested from Tweak config
        self.createConnections()

        if self.tweak.hasGUI:
            # Have to load GUI first (at least with Caiman) #TODO: Fix Caiman instead?
            name = self.tweak.gui.name
            m = self.tweak.gui # m is TweakModule 
            # treat GUI uniquely since user communication comes from here
            try:
                visualClass = m.options['visual']
                # need to instantiate this module 
                visualModule = self.tweak.modules[visualClass]
                self.createModule(visualClass, visualModule)
                # then add links for visual
                for k,l in {key:self.data_queues[key] for key in self.data_queues.keys() if visualClass in key}.items():
                    self.assignLink(k, l)

                #then give it to our GUI
                self.createModule(name, m)
                self.modules[name].setup(visual=self.modules[visualClass])

                self.p_GUI = Process(target=self.modules[name].run)
                self.p_GUI.daemon = True
                self.p_GUI.start()

            except Exception as e:
                logger.error('Exception in setting up GUI {}'.format(name)+': {}'.format(e))

        # First set up each class/module
        for name,module in self.tweak.modules.items():
            if name not in self.modules.keys(): 
                #Check for modules being instantiated twice
                self.createModule(name, module)

        # Second set up each connection b/t modules
        for name,link in self.data_queues.items():
            self.assignLink(name, link)

        #TODO: links multi created for visual after visual in separate process?
        #TODO: error handling for is a user tries to use q_in without defining it

    def createModule(self, name, module):
        ''' Function to instantiate module, add signal and comm Links,
            and update self.modules dictionary
        '''
        # Instantiate selected class
        mod = import_module(module.packagename)
        clss = getattr(mod, module.classname)
        instance = clss(module.name)

        # Add link to Limbo store
        instance.setStore(store.Limbo(module.name))

        # Add signal and communication links
        q_comm = Link(module.name+'_comm', module.name, self.name)
        q_sig = Link(module.name+'_sig', self.name, module.name)
        self.comm_queues.update({q_comm.name:q_comm})
        self.sig_queues.update({q_sig.name:q_sig})
        instance.setLinks(q_comm, q_sig)

        # Update information
        self.modules.update({name:instance})

    def createConnections(self):
        ''' Assemble links (multi or other)
            for later assignment
        '''
        for source,drain in self.tweak.connections.items():
            name = source.split('.')[0]
            #current assumption is connection goes from q_out to something(s) else
            if len(drain) > 1: #we need multiasyncqueue 
                link, endLinks = MultiLink(name+'_multi', source, drain)
                self.data_queues.update({source:link})
                for i,e in enumerate(endLinks):
                    self.data_queues.update({drain[i]:e})
            else: #single input, single output
                d = drain[0]
                d_name = d.split('.')
                link = Link(name+'_'+d_name[0], source, d)
                self.data_queues.update({source:link})
                self.data_queues.update({d:link})

    def assignLink(self, name, link):
        ''' Function to set up Links between modules
            for data location passing
            Module must already be instantiated

            #NOTE: Could use this for reassigning links if modules crash?
        '''
        #logger.info('Assigning link {}'.format(name))
        classname = name.split('.')[0]
        linktype = name.split('.')[1]
        if linktype == 'q_out':
            self.modules[classname].setLinkOut(link)
        elif linktype == 'q_in':
            self.modules[classname].setLinkIn(link)
        else:
            self.modules[classname].addLink(linktype, link)

    def createNexus(self):
        self._startStore(100000000000) #default size should be system-dependent
    
        #connect to store and subscribe to notifications
        self.limbo = store.Limbo()
        self.limbo.subscribe()

        self.comm_queues = {}
        self.sig_queues = {}
        self.data_queues = {}
        self.modules = {}
        self.flags = {}
        self.processes = []

        self.loadTweak() #TODO: filename?

        self.flags.update({'quit':False, 'run':False, 'load':False})

    def setupAll(self):
        '''Setup all modules
        '''
        for name,m in self.tweak.modules.items(): # m is TweakModule 
            try: #self.modules[name] is the module instance
                self.modules[name].setup(**m.options)
            except Exception as e:
                logger.error('Exception in setting up module {}'.format(name)+': {}'.format(e))

        logger.info('Finished setup for all modules')

    def runModule(self, module):
        '''Run the module continually; for in separate process
        '''
        module.run()

    def startNexus(self):
        ''' Puts all modules in separate processes and begins polling
            to listen to comm queues
        '''
        for name,m in self.modules.items(): #m accesses the specific module instance
            if 'GUI' not in name: #GUI already started
                p = Process(target=self.runModule, args=(m,))
                p.daemon = True
                self.processes.append(p)
                #TODO: os.nice() for priority?

        loop = asyncio.get_event_loop()

        signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
        for s in signals:
            loop.add_signal_handler(
                s, lambda s=s: asyncio.create_task(stop_polling(s, loop)))

        loop.run_until_complete(self.pollQueues()) #TODO: in Link executor, complete all tasks

    def run(self):
        logger.info('Starting processes')
        self.t = time.time()
        
        for p in self.processes:
            print(p)
            p.start()

        for q in self.sig_queues.values():
            try:
                q.put_nowait(Spike.run())
            except Full as f:
                logger.warning('Signal queue'+q.name+'is full')
                #queue full, keep going anyway TODO: add repeat trying as async task

    def quit(self):
        with open('timing/noticiations.txt', 'w') as output:
            output.write(str(self.listing))
        
        logger.warning('Killing child processes')
        
        for q in self.sig_queues.values():
            try:
                q.put_nowait(Spike.quit())
            except Full as e:
                logger.warning('Signal queue '+q.name+' full, cannot tell it to quit')

        self.processes.append(self.p_GUI)
        for p in self.processes:
            if p.is_alive():
                p.terminate()
            p.join()

        logger.warning('Done with available frames')
        print('total time ', time.time()-self.t)

        self.destroyNexus()

    async def pollQueues(self):
        self.listing = []
        gui_fut = None
        acq_fut = None
        proc_fut = None
        polling = list(self.comm_queues.values())
        pollingNames = list(self.comm_queues.keys())
        tasks = []
        for q in polling:
            tasks.append(asyncio.ensure_future(q.get_async()))

        while not self.flags['quit']:   
            done, pending = await asyncio.wait(tasks, return_when=concurrent.futures.FIRST_COMPLETED)
            #TODO: actually kill pending tasks
            
            for i,t in enumerate(tasks):
                if t in done or polling[i].status == 'done': #catch tasks that complete await wait/gather
                    r = polling[i].result
                    if 'GUI' in pollingNames[i]:
                        self.processGuiSignal(r)
                    else:
                        self.processModuleSignal(r, pollingNames[i])
                    tasks[i] = (asyncio.ensure_future(polling[i].get_async()))

            # try:
            #     print('Store has ', len(self.limbo.get_all()), ' objects')
            # except:
            #     pass
            self.listing.append(self.limbo.notify())

        logger.warning('Shutting down polling')

    def processGuiSignal(self, flag):
        '''Receive flags from the Front End as user input
            List of flags: 0 = run(), 1 = quit, 2 = load tweak
        '''
        logger.info('Received signal from GUI: '+flag[0])
        if flag[0] in self.flags.keys():
            if flag[0] == Spike.run():
                logger.info('Begin run!')
                self.flags['run'] = True
                self.run()
            elif flag[0] == Spike.quit():
                logger.warning('Quitting the program!')
                self.flags['quit'] = True
                self.quit()
            elif flag[0] == Spike.load():
                logger.info('Loading Tweak config from file '+flag[1])
                self.loadTweak(flag[1])
            elif flag[0] == Spike.stop():
                logger.info('Stopping processes')
                # TODO. Also pause, resume, reset
        else:
            logger.error('Signal received from Nexus but cannot identify {}'.format(flag))

    def processModuleSignal(self, sig, name):
        pass
        #if sig is not None:
        #    logger.info('Received signal '+str(sig[0])+' from '+name)
        #TODO

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
            self.p_Limbo.kill()
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
            self.p_Limbo = subprocess.Popen(['plasma_store',
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

    def __repr__(self):
        #return str(self.__class__) + ": " + str(self.__dict__)
        return 'Link '+self.name #+' From: '+self.start+' To: '+self.end

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


def MultiLink(name, start, end):
    ''' End is a list

        Return a MultiAsyncQueue as q (for producer) and list of AsyncQueues as q_out (for consumers)
    '''
    m = Manager()

    q_out = []
    for endpoint in end:
        q = AsyncQueue(m.Queue(maxsize=0), name, start, endpoint)
        q_out.append(q)

    q = MultiAsyncQueue(m.Queue(maxsize=0), q_out, name, start, end)

    return q, q_out

class MultiAsyncQueue(AsyncQueue):
    ''' Extension of AsyncQueue created by Link to have multiple endpoints.
        A single producer queue's 'put' is copied to multiple consumer's queues
        q_in is the producer queue, q_out are the consumer queues

        #TODO: test the async nature of this group of queues
    '''
    def __init__(self, q_in, q_out, name, start, end):
        self.queue = q_in
        self.output = q_out

        self.real_executor = None
        self.cancelled_join = False

        self.name = name
        self.start = start
        self.end = end[0] #somewhat arbitrary endpoint naming
        self.status = 'pending'
        self.result = None

    def __repr__(self):
        #return str(self.__class__) + ": " + str(self.__dict__)
        return 'MultiLink '+self.name 
    
    def __getattr__(self, name):
        # Remove put and put_nowait and define behavior specifically
        #TODO: remove get capability
        if name in ['qsize', 'empty', 'full',
                    'get', 'get_nowait', 'close']:
            return getattr(self.queue, name)
        else:
            raise AttributeError("'%s' object has no attribute '%s'" % 
                                    (self.__class__.__name__, name))

    def put(self, item):
        for q in self.output:
            q.put(item)

    def put_nowait(self, item):
        for q in self.output:
            q.put_nowait(item)



if __name__ == '__main__':
    nexus = Nexus('Nexus')
    nexus.createNexus()
    nexus.setupAll()
    
    #cwd = os.getcwd()
    #nexus.setupAcquirer(cwd+'/../data/Eva/zf1.h5')
    
    nexus.startNexus() #start polling, create processes
    
    
    