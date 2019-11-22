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

    async def count(self):
        self.runlist.append(1) 
        await asyncio.sleep(1)
        self.runlist.append(2)

    async def main(self):
        await asyncio.gather(self.count(), self.count(), self.count())

    def process(self):
        asyncio.run(self.main())
    
    async def createAsyncProcess(self, q_sig, q_comm):
        async with AsyncRunManager('test', self.process_run, self.process_setup, q_sig, q_comm) as rm:
            print(rm)

    async def runProcess(self, q_sig, q_comm):
        self.p2 = Process(target= self.createAsyncProcess, args= (self.q_sig, self.q_comm,))
        self.p2.start()
        self.q_sig.put('setup')
        self.q_sig.put('run')
        self.q_sig.put('pause')
        self.q_sig.put('resume')
        self.q_sig.put('quit')
        self.p2.terminate()
        self.p2.kill()

    async def a_put(self, signal, time):
        await asyncio.sleep(time)
        self.q_sig.put_async(signal)      
