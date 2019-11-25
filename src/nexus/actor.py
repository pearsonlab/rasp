import asyncio
from queue import Empty
import time
from typing import Awaitable, Callable
import traceback

import logging; logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Actor():
    '''Abstract class for an actor that Nexus
       controls and interacts with.
       Needs to have a store and links for communication
       Also needs at least a setup and run function
    '''
    def __init__(self, name, links={}, **kwargs):
        ''' Require a name for multiple instances of the same actor/class
            Create initial empty dict of Links for easier referencing
        '''
        self.name = name
        self.links = links
        self.done = False # TODO: obsolete, remove

        self.lower_priority = False 

        # start with no explicit data queues.             
        # q_in and q_out are for passing ID information to access data in the store
        self.q_in = None
        self.q_out = None

    def __repr__(self):
        ''' Return this instance name and links dict
        '''
        return self.name+': '+str(self.links.keys())

    def setStore(self, client):
        '''Set client interface to the store
        '''
        self.client = client

    def setLinks(self, links):
        ''' General full dict set for links
        '''
        self.links = links

    def setCommLinks(self, q_comm, q_sig):
        ''' Set explicit communication links to/from Nexus (q_comm, q_sig)
            q_comm is for messages from this actor to Nexus
            q_sig is signals from Nexus and must be checked first
        '''
        self.q_comm = q_comm
        self.q_sig = q_sig
        self.links.update({'q_comm':self.q_comm, 'q_sig':self.q_sig})

    def setLinkIn(self, q_in):
        ''' Set the dedicated input queue
        '''
        self.q_in = q_in
        self.links.update({'q_in':self.q_in})

    def setLinkOut(self, q_out):
        ''' Set the dedicated output queue
        '''
        self.q_out = q_out
        self.links.update({'q_out':self.q_out})

    def addLink(self, name, link):
        ''' Function provided to add additional data links by name
            using same form as q_in or q_out
            Must be done during registration and not during run
        '''
        self.links.update({name:link})
        # User can then use: self.my_queue = self.links['my_queue'] in a setup fcn,
        # or continue to reference it using self.links['my_queue']

    def getLinks(self):
        ''' Returns dictionary of links
        '''
        return self.links

    def setup(self):
        ''' Essenitally the registration process
            Can also be an initialization for the actor
            options is a list of options, can be empty
        '''
        raise NotImplementedError

    def run(self):
        ''' Must run in continuous mode
            Also must check q_sig either at top of a run-loop
            or as async with the primary function
        '''
        raise NotImplementedError

        ''' Suggested implementation for synchronous running: see RunManager class below
        TODO: define async example that checks for signals _while_ running
        '''

    def changePriority(self):
        ''' Try to lower this process' priority
            Only changes priority if lower_priority is set
            TODO: Only works on unix machines. Add Windows functionality
        '''
        if self.lower_priority is True:
            import os, psutil
            p = psutil.Process(os.getpid())
            p.nice(19) #lowest as default
            logger.info('Lowered priority of this process: {}'.format(self.name))
            print('Lowered ', os.getpid(), ' for ', self.name)


class Spike():
    ''' Class containing definition of signals Nexus uses
        to communicate with its actors
        TODO: doc each of these with expected handling behavior
        NOTE: add functionality as class objects..? Any advantage to this?
    '''
    @staticmethod
    def run():
        return 'run'

    @staticmethod
    def quit():
        return 'quit'

    @staticmethod
    def pause():
        return 'pause'

    @staticmethod
    def resume():
        return 'resume'

    @staticmethod
    def reset(): #TODO: implement in Nexus
        return 'reset'
    
    @staticmethod
    def load():
        return 'load'

    @staticmethod
    def setup():
        return 'setup'

    @staticmethod
    def ready():
        return 'ready'


class RunManager():
    '''
    TODO: make async version of runmanager
    '''
    def __init__(self, name, runMethod, setup, q_sig, q_comm):
        self.run = False
        self.config = False
        self.runMethod = runMethod
        self.setup = setup
        self.q_sig = q_sig
        self.q_comm = q_comm
        self.actorName = name

        #TODO make this tunable
        self.timeout = 0.000001

    def __enter__(self):
        self.start = time.time()

        while True:
            if self.run:
                try:
                    self.runMethod() #subfunction for running singly
                except Exception as e:
                    logger.error('Actor '+self.actorName+' exception during run: {}'.format(e))
                    print(traceback.format_exc())
            elif self.config:
                try:
                    self.setup() #subfunction for setting up the actor
                    self.q_comm.put([Spike.ready()])
                except Exception as e:
                    logger.error('Actor '+self.actorName+' exception during setup: {}'.format(e))  
                    raise Exception
                self.config = False #Run once
            try: 
                signal = self.q_sig.get(timeout=self.timeout)
                if signal == Spike.run(): 
                    self.run = True
                    logger.warning('Received run signal, begin running')
                elif signal == Spike.setup():
                    self.config = True
                elif signal == Spike.quit():
                    logger.warning('Received quit signal, aborting')
                    break
                elif signal == Spike.pause():
                    logger.warning('Received pause signal, pending...')
                    self.run = False
                elif signal == Spike.resume(): #currently treat as same as run
                    logger.warning('Received resume signal, resuming')
                    self.run = True
            except Empty as e:
                pass #no signal from Nexus
        return None #Status...?


    def __exit__(self, type, value, traceback):
        logger.info('Ran for '+str(time.time()-self.start)+' seconds')
        logger.warning('Exiting RunManager')
        return None


class AsyncRunManager():
    '''
    Asynchronous run manager. Communicates with nexus core using q_sig and q_comm.
    To be used with [async with].
    Afterwards, the run manager listens for signals without blocking.
    q_sig, q_comm are AsyncQueues
    '''

    def __init__(self, name, run_method, setup, q_sig, q_comm):
        self.run = False
        self.config = False
        self.run_method = run_method
        self.setup = setup
        self.q_sig = q_sig
        self.q_comm = q_comm
        self.module_name = name
        self.loop = asyncio.get_event_loop()
        self.start = time.time()

    async def __aenter__(self):
        while True:
            signal = await self.q_sig.get_async()
            if signal == Spike.run() or signal == Spike.resume():
                if not self.run:
                    self.run = True
                    asyncio.ensure_future(self.run_method(), loop=self.loop)
                    print('Received run signal, begin running')
            elif signal == Spike.setup():
                self.setup()
                await self.q_comm.put_async([Spike.ready()])
            elif signal == Spike.quit():
                logger.warning('Received quit signal, aborting')
                self.loop.stop()
                break
            elif signal == Spike.pause():
                logger.warning('Received pause signal, pending...')
                while self.q_sig.get() != Spike.resume():  # Intentionally blocking TODO
                    time.sleep(1e-3)

    async def __aexit__(self, value, traceback):
        logger.info('Ran for {} seconds'.format(time.time() - self.start))
        logger.warning('Exiting AsyncRunManager')
