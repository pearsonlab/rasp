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

    def __str__(self):
        ''' Return this instance name
        '''
        return self.name

    def setStore(self, client):
        '''Set client interface to the store
        '''
        self.client = client

    def setLinks(self, q_comm, q_sig, q_in=None, q_out=None):
        ''' Set explicit links (q_in, q_out, q_comm, q_sig)
            q_in and q_out are for passing ID information to access data in the store
            q_comm is for messages from this module to Nexus
            q_sig is signals from Nexus and must be checked first
            Default is None for data queues, for eg., Acquirer module has no input queue
        '''
        self.q_comm = q_comm
        self.q_sig = q_sig
        self.q_in = q_in
        self.q_out = q_out
        self.links.update({'q_comm':self.q_comm, 'q_sig':self.q_sig, 'q_in':self.q_in, 'q_out':self.q_out})

    def addLink(self, link):
        ''' Function provided to add additional data links 
            using same form as q_in or q_out
            Must be done during registration and not during run
            TODO: Test this function
        '''
        self.links.update({link.name:link})

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

class Spike():
    ''' Class containing definition of signals Nexus uses
        to communicate with its modules
        TODO: doc each of these with expected handling behavior
        TODO: rename Radar?
    '''
    def run():
        return 'run'

    def quit():
        return 'quit'

    def pause():
        return 'pause'

    def resume():
        return 'resume'

    def reset():
        return 'reset'