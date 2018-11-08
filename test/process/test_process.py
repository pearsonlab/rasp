from unittest import TestCase
from test.test_utils import StoreDependentTestCase
from src.nexus.store import Limbo
from src.process.process import CaimanProcessor as cp

class Caiman_Setup(StoreDependentTestCase):
    ''' Test creation of OnACID object and store connection
    '''

    def setUp(self):
        super(Caiman_Setup, self).setUp()
        self.limbo = Limbo()
        self.proc = cp('caiman', self.limbo)

    def test_StartProc(self):
        params = self.limbo.put({'fnames': '/Users/hawkwings/Documents/Neuro/RASP/rasp/data/Tolias_mesoscope_1.hdf5'}, 'params')
        cp.setupProcess(self.proc, 'params')
        self.assertTrue(1)
    
    #def test_runProc(self):
    #
    #    cp.runProcess(self.proc, frames, output)

    def tearDown(self):
        super(Caiman_Setup, self).tearDown()