import sys
import os
import time
import subprocess
from multiprocessing import Process, Queue, Manager, cpu_count, set_start_method
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
from nexus.actor import Spike
from queue import Empty, Full
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG,
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

    def createNexus(self, file=None):
        self._startStore(40000000000) #default size should be system-dependent; this is 40 GB

        #connect to store and subscribe to notifications
        self.limbo = store.Limbo()
        self.limbo.subscribe()

        self.comm_queues = {}
        self.sig_queues = {}
        self.data_queues = {}
        self.actors = {}
        self.flags = {}
        self.processes = []

        #self.startWatcher()

        self.loadTweak(file=file)

        self.flags.update({'quit':False, 'run':False, 'load':False})
        self.allowStart = False

    def startNexus(self):
        ''' Puts all actors in separate processes and begins polling
            to listen to comm queues
        '''
        for name,m in self.actors.items(): #m accesses the specific actor class instance
            if 'GUI' not in name: #GUI already started
                p = Process(target=self.runActor, name=name, args=(m,))
                p.daemon = True
                self.processes.append(p)

        self.start()

        loop = asyncio.get_event_loop()

        signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
        for s in signals:
            loop.add_signal_handler(
                s, lambda s=s: asyncio.ensure_future(self.stop_polling(s, loop))) #TODO

        loop.run_until_complete(self.pollQueues()) #TODO: in Link executor, complete all tasks

    def loadTweak(self, file=None):
        ''' For each connection:
            create a Link with a name (purpose), start, and end
            Start links to one actor's name, end to the other.
            Nexus gives start_actor the Link as a q_in,
              and end_actor the Link as a q_out
            Nexus maintains dict of name and associated Link.
            Nexus also has list of Links that it is itself connected to
              for communication purposes.
            OR
            For each connection, create 2 Links. Nexus acts as intermediary.
        '''
        #TODO load from file or user input, as in dialogue through FrontEnd?

        self.tweak = Tweak(configFile = file)
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
                # need to instantiate this actor
                visualActor = self.tweak.actors[visualClass]
                self.createActor(visualClass, visualActor)
                # then add links for visual
                for k,l in {key:self.data_queues[key] for key in self.data_queues.keys() if visualClass in key}.items():
                    self.assignLink(k, l)

                #then give it to our GUI
                self.createActor(name, m)
                self.actors[name].setup(visual=self.actors[visualClass])

                self.p_GUI = Process(target=self.actors[name].run, name=name)
                self.p_GUI.daemon = True
                self.p_GUI.start()

            except Exception as e:
                logger.error('Exception in setting up GUI {}'.format(name)+': {}'.format(e))

        # First set up each class/actor
        for name,actor in self.tweak.actors.items():
            if name not in self.actors.keys():
                #Check for actors being instantiated twice
                self.createActor(name, actor)

        # Second set up each connection b/t actors
        for name,link in self.data_queues.items():
            self.assignLink(name, link)

        #TODO: error handling for if a user tries to use q_in without defining it

    def createActor(self, name, actor):
        ''' Function to instantiate actor, add signal and comm Links,
            and update self.actors dictionary
        '''
        # Instantiate selected class
        mod = import_module(actor.packagename)
        clss = getattr(mod, actor.classname)
        instance = clss(actor.name, **actor.options)

        # Add link to Limbo store
        instance.setStore(store.Limbo(actor.name))

        # Add signal and communication links
        q_comm = Link(actor.name+'_comm', actor.name, self.name)
        q_sig = Link(actor.name+'_sig', self.name, actor.name)
        self.comm_queues.update({q_comm.name:q_comm})
        self.sig_queues.update({q_sig.name:q_sig})
        instance.setCommLinks(q_comm, q_sig)

        # Update information
        self.actors.update({name:instance})

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
                d_name = d.split('.') #TODO: check if .anything, if not assume q_in
                link = Link(name+'_'+d_name[0], source, d)
                self.data_queues.update({source:link})
                self.data_queues.update({d:link})

    def assignLink(self, name, link):
        ''' Function to set up Links between actors
            for data location passing
            Actor must already be instantiated

            #NOTE: Could use this for reassigning links if actors crash?
            #TODO: Adjust to use default q_out and q_in vs being specified
        '''
        #logger.info('Assigning link {}'.format(name))
        classname = name.split('.')[0]
        linktype = name.split('.')[1]
        if linktype == 'q_out':
            self.actors[classname].setLinkOut(link)
        elif linktype == 'q_in':
            self.actors[classname].setLinkIn(link)
        else:
            self.actors[classname].addLink(linktype, link)

    def runActor(self, actor):
        '''Run the actor continually; used for separate processes
            #TODO: hook into monitoring here?
        '''
        actor.run()

    def startWatcher(self):
        self.watcher = store.Watcher('watcher', store.Limbo('watcher'))
        q_sig = Link('watcher_sig', self.name, 'watcher')
        self.watcher.setLinks(q_sig)
        self.sig_queues.update({q_sig.name:q_sig})

        self.p_watch = Process(target=self.watcher.run, name='watcher_process')
        self.p_watch.daemon = True
        self.p_watch.start()

    def start(self):
        logger.info('Starting processes')
        self.t = time.time()

        for p in self.processes:
            p.start()

    def setup(self):
        for q in self.sig_queues.values():
            try:
                q.put_nowait(Spike.setup())
            except Full:
                logger.warning('Signal queue'+q.name+'is full')

    def run(self):
        if self.allowStart:
            for q in self.sig_queues.values():
                try:
                    q.put_nowait(Spike.run())
                except Full:
                    logger.warning('Signal queue'+q.name+'is full')
                    #queue full, keep going anyway TODO: add repeat trying as async task

    def quit(self):
        # with open('timing/noticiations.txt', 'w') as output:
        #     output.write(str(self.listing))

        logger.warning('Killing child processes')

        for q in self.sig_queues.values():
            try:
                q.put_nowait(Spike.quit())
            except Full as f:
                logger.warning('Signal queue '+q.name+' full, cannot tell it to quit: {}'.format(f))

        self.processes.append(self.p_GUI)
        #self.processes.append(self.p_watch)
        for p in self.processes:
            # if p.is_alive():
            #     p.terminate()
            p.join()

        logger.warning('Done with available frames')
        print('total time ', time.time()-self.t)

        self.destroyNexus()

    async def pollQueues(self):
        self.listing = [] #TODO: Remove or rewrite
        self.actorStates = dict.fromkeys(self.actors.keys())
        if not self.tweak.hasGUI:  # Since Visual is not started, it cannot send a ready signal.
            try:
                del self.actorStates['Visual']
            except:
                pass
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
                        self.processGuiSignal(r, pollingNames[i])
                    else:
                        self.processActorSignal(r, pollingNames[i])
                    tasks[i] = (asyncio.ensure_future(polling[i].get_async()))

            #self.listing.append(self.limbo.notify())

        logger.warning('Shutting down polling')

    def processGuiSignal(self, flag, name):
        '''Receive flags from the Front End as user input
            TODO: Not all needed
        '''
        name = name.split('_')[0]
        logger.info('Received signal from GUI: '+flag[0])
        if flag[0]:
            if flag[0] == Spike.run():
                logger.info('Begin run!')
                #self.flags['run'] = True
                self.run()
            elif flag[0] == Spike.setup():
                logger.info('Running setup')
                self.setup()
            elif flag[0] == Spike.ready():
                logger.info('GUI ready')
                self.actorStates[name] = flag[0]
            elif flag[0] == Spike.quit():
                logger.warning('Quitting the program!')
                self.flags['quit'] = True
                self.quit()
            elif flag[0] == Spike.load():
                logger.info('Loading Tweak config from file '+flag[1])
                self.loadTweak(flag[1])
            elif flag[0] == Spike.pause():
                logger.info('Pausing processes')
                # TODO. Alsoresume, reset
        else:
            logger.error('Signal received from Nexus but cannot identify {}'.format(flag))

    def processActorSignal(self, sig, name):
        if sig is not None:
            logger.info('Received signal '+str(sig[0])+' from '+name)
            if sig[0]==Spike.ready():
                self.actorStates[name.split('_')[0]] = sig[0]
                if all(val==Spike.ready() for val in self.actorStates.values()):
                    self.allowStart = True      #TODO: replace with q_sig to FE/Visual
                    logger.info('Allowing start')

                    #TODO: Maybe have flag for auto-start, else require explict command
                    # if not self.tweak.hasGUI:
                    #     self.run()

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

    async def stop_polling(self, signal, loop):
        ''' TODO: update asyncio library calls
        '''
        logging.info('Received exit signal {}'.format(signal.name))

        tasks = [t for t in asyncio.Task.all_tasks() if t is not
                asyncio.Task.current_task()]

        [task.cancel() for task in tasks]

        #TODO: Fix for hanging behavior
        logging.info('Canceling outstanding tasks')
        await asyncio.gather(*tasks)
        loop.stop()
        logging.info('Shutdown complete.')


def Link(name, start, end):
    ''' Abstract constructor for a queue that Nexus uses for
    inter-process/actor signaling and information passing

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
            self.status = 'done'
            return self.result
        except Exception as e:
            logger.exception('Error in get_async: {}'.format(e))
            pass

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
    # set_start_method('fork')

    nexus = Nexus('Nexus')
    nexus.createNexus(file='exp_oct21_demo.yaml')
    nexus.startNexus() #start polling, create processes    
