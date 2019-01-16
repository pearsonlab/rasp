from unittest import TestCase
from test.test_utils import StoreDependentTestCase
from src.acquire.acquire import FileAcquirer
from src.nexus.store import Limbo

class Acquirer_Setup(StoreDependentTestCase):
    ''' Test creation of FileAcquirer object and store connection
        along with various components
    '''

    def setUp(self):
        super(Acquirer_Setup, self).setUp()
        self.limbo = Limbo()
        self.acq = FileAcquirer('acq', self.limbo)
        self.acq.setupAcquirer('/Users/hawkwings/Documents/Neuro/RASP/rasp/data/Tolias_mesoscope_1.hdf5')

    # def test_init(self):
    #     #self.acq.setupAcquirer('/Users/hawkwings/Documents/Neuro/RASP/rasp/data/zf1.h5')
    #     self.assertTrue(1)
    
    def test_frame_acq(self):
        #self.acq.setupAcquirer('/Users/hawkwings/Documents/Neuro/RASP/rasp/data/zf1.h5')
        frame = self.acq.getFrame(1)
        print(frame.shape)
        self.assertTrue(frame.shape==(440,256))

    def test_store_frame(self):
        for _ in range(1010):
            self.acq.runAcquirer()
        frame = self.limbo.get('curr_frame')
        self.assertTrue(frame.shape==(440,256))

    def tearDown(self):
        super(Acquirer_Setup, self).tearDown()