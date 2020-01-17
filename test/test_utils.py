from unittest import TestCase
import subprocess
import asyncio
from nexus.actor import RunManager, AsyncRunManager
from multiprocessing import Process

class StoreDependentTestCase(TestCase):
    ''' Unit test base class that starts the Limbo plasma server
        for the tests in this case.
    '''

    def setUp(self):
        ''' Start the server
        '''
        self.p = subprocess.Popen(['plasma_store',
                              '-s', '/tmp/store',
                              '-m', str(10000000)],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)

    def tearDown(self):
        ''' Kill the server
        '''

        self.p.kill()

class ActorDependentTestCase(TestCase):

    def setUp(self):
        ''' Start the server
        '''
        self.p = subprocess.Popen(['plasma_store',
                              '-s', '/tmp/store',
                              '-m', str(10000000)],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)

    def tearDown(self):
        ''' Kill the server
        '''

        self.p.kill()

    def run_setup(self):
        self.isSetUp= True

    def runMethod(self):
        self.runNum+=1

    def process_setup(self):
        pass

    def process_run(self):
        self.q_comm.put('ran')

    def createprocess(self, q_sig, q_comm):
        with RunManager('test', self.process_run, self.process_setup, q_sig, q_comm) as rm:
            print(rm)

    async def createAsyncProcess(self, q_sig, q_comm):
        async with AsyncRunManager('test', self.process_run, self.process_setup, q_sig, q_comm) as rm:
            print(rm)

    async def a_put(self, signal, time):
        await asyncio.sleep(time)
        self.q_sig.put_async(signal)
