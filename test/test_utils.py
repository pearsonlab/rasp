from unittest import TestCase
import subprocess
import asyncio

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

    def run_setup(self):
        self.isSetUp= True

    def runMethod(self):
        self.runNum+=1

    async def a_put(self, signal, time):
        await asyncio.sleep(time)
        self.q_sig.put_async(signal)

    def tearDown(self):
        ''' Kill the server
        '''

        self.p.kill()
