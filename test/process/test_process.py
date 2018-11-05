from unittest import TestCase
from test.test_utils import StoreDependentTestCase
from src.process.process import CaimanProcessor as cp

class Caiman_Setup(StoreDependentTestCase):
    ''' Test creation of OnACID object and store connection
    '''

    def setUp(self):
        super(Caiman_Setup, self).setUp()
        self.proc = cp('caiman')


    def tearDown(self):
        super(Caiman_Setup, self).tearDown()