
from unittest import TestCase
from test.test_utils import StoreDependentTestCase
from src.nexus.store import Limbo
from multiprocessing import Process

class Limbo_Get(StoreDependentTestCase):
    
    def setUp(self):
        super(Limbo_Get, self).setUp()
        self.limbo = Limbo()

    def test_init_empty(self):
        self.assertFalse(self.limbo.get_all())

    def tearDown(self):
        super(Limbo_Get, self).tearDown()


class Limbo_Put(StoreDependentTestCase):
    
    def setUp(self):
        super(Limbo_Put, self).setUp()
        self.limbo = Limbo()

    def test_putOne(self):
        id = self.limbo.put(1, 'one')
        self.assertEqual(1, self.limbo.get('one'))
    
    def tearDown(self):
        super(Limbo_Put, self).tearDown()


class Limbo_PutGet(StoreDependentTestCase):
    
    def setUp(self):
        super(Limbo_PutGet, self).setUp()
        self.limbo = Limbo()

    def test_getOne(self):
        id = self.limbo.put(1, 'one')
        id2 = self.limbo.put(2, 'two')
        self.assertEqual(1, self.limbo.get('one'))
        self.assertEqual(id, self.limbo.stored['one'])
    
    def tearDown(self):
        super(Limbo_PutGet, self).tearDown()


