class Module():
    '''Abstract class for a module that Nexus
       controls and interacts with.
       Needs to have a store and links for communication
       Also needs at least a setup and run function
    '''
    def __init__(self, name):
        ''' Require a name for multiple instances of the same module/class
            Create initial empty dict of Links for easier referencing
        '''
        self.name = name
        self.links = {}
        self.done = False #Needed?

        # start with no explicit data queues.             
        # q_in and q_out are for passing ID information to access data in the store
        self.q_in = None
        self.q_out = None

    def __repr__(self):
        ''' Return this instance name and links dict
        '''
        return self.name+': '+str(self.links)

    def setStore(self, client):
        '''Set client interface to the store
        '''
        self.client = client

    def setLinks(self, q_comm, q_sig):
        ''' Set explicit links (q_comm, q_sig)
            q_comm is for messages from this module to Nexus
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

    def addLink(self, link):
        ''' Function provided to add additional data links 
            using same form as q_in or q_out
            Must be done during registration and not during run
            TODO: Test this function
        '''
        self.links.update({link.name:link})
        # User can then use: self.my_queue = self.links['my_queue'] in a setup fcn,
        # or continue to reference it using self.links['my_queue']

    def setup(self):
        ''' Essenitally the registration process
            Can also be an initialization for the module
        '''
        raise NotImplementedError

    def run(self):
        ''' Must run in continuous mode
            Also must check q_sig either at top of a run-loop
            or as async with the primary function
        '''
        raise NotImplementedError

        ''' Suggested implementation for synchronous running
        TODO: define async example that checks for signals _while_ running
        TODO: Make this a context manager
        while True:
            if self.flag:
                try:
                    self.runModule() #subfunction for running singly
                    if self.done:
                        logger.info('Module is done, exiting')
                        return
                except Exception as e:
                    logger.error('Module exception during run: {}'.format(e))
                    break 
            try: 
                signal = self.q_sig.get(timeout=1)
                if signal == Spike.run(): 
                    self.flag = True
                    logger.warning('Received run signal, begin running')
                elif signal == Spike.quit():
                    logger.warning('Received quit signal, aborting')
                    break
                elif signal == Spike.pause():
                    logger.warning('Received pause signal, pending...')
                    self.flag = False
                elif signal == Spike.resume(): #currently treat as same as run
                    logger.warning('Received resume signal, resuming')
                    self.flag = True
            except Empty as e:
                pass #no signal from Nexus
        '''

class Spike():
    ''' Class containing definition of signals Nexus uses
        to communicate with its modules
        TODO: doc each of these with expected handling behavior
    '''
    def run():
        return 'run'

    def quit():
        return 'quit'

    def pause():
        return 'pause'

    def resume():
        return 'resume'

    def reset(): #TODO
        return 'reset'


class RunManager():
    def __init__(self):
        self.flag = False

    def __enter__(self):
        if self.flag:
            try:
                self.runModule() #subfunction for running singly
                if self.done: #TODO: require this in module?
                    logger.info('Module is done, exiting')
                    return
            except Exception as e:
                logger.error('Module exception during run: {}'.format(e))
                #break 
        try: 
            signal = self.q_sig.get(timeout=1)
            if signal == Spike.run(): 
                self.flag = True
                logger.warning('Received run signal, begin running')
            elif signal == Spike.quit():
                logger.warning('Received quit signal, aborting')
                #self.flag = False  #FIXME
                self.done = True
            elif signal == Spike.pause():
                logger.warning('Received pause signal, pending...')
                self.flag = False
            elif signal == Spike.resume(): #currently treat as same as run
                logger.warning('Received resume signal, resuming')
                self.flag = True
        except Empty as e:
            pass #no signal from Nexus

    def __exit__(self):
        pass