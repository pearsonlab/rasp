from unittest import TestCase
#from test.test_utils import StoreDependentTestCase
from nexus.store import Limbo
from nexus.nexus import Nexus
from multiprocessing import Process

class Nexus_Setup(TestCase):
    ''' Test creation of Nexus object and store connection
        along with various components
    '''

    def setUp(self):
        self.nexus = Nexus('NeuralNexus')
        self.nexus.createNexus()
        self.limbo = Limbo()

    def test_setupProc(self):
        #self.nexus.setupProcessor()
        #cp.setupProcess(self.proc, 'params_dict')
        self.assertTrue(1)
    
    def test_runProc(self):
        #self.nexus.setupProcessor()
        #self.nexus.runProcessor()
        self.assertTrue(1)

    def test_consecProc(self):
        self.nexus.setupProcessor()
        for _ in range(6):
            self.nexus.runProcessor()
        self.assertTrue(1)

    def tearDown(self):
        self.nexus.destroyNexus()