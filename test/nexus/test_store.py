
from unittest import TestCase
from test.test_utils import StoreDependentTestCase
from src.nexus.store import Limbo

class Store_Get(StoreDependentTestCase):
    
    def setUp(self):
        super(Store_Get, self).setUp()
        self.limbo = Limbo()

    def test_init_empty(self):
        self.assertFalse(self.limbo.get_all())

    def tearDown(self):
        super(Store_Get, self).tearDown()


class Store_Put(StoreDependentTestCase):
    
    def setUp(self):
        super(Store_Put, self).setUp()
        self.limbo = Limbo()

    def test_putOne(self):
        id = self.limbo.put(1, 'one')
        self.assertEqual(1, self.limbo.get('one'))
    
    def tearDown(self):
        super(Store_Put, self).tearDown()

