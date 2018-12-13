
from unittest import TestCase
from test.test_utils import StoreDependentTestCase
from src.nexus.store import Limbo
from multiprocessing import Process

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


class Store_PutGet(StoreDependentTestCase):
    
    def setUp(self):
        super(Store_PutGet, self).setUp()
        self.limbo = Limbo()

    def test_getOne(self):
        id = self.limbo.put(1, 'one')
        id2 = self.limbo.put(2, 'two')
        self.assertEqual(1, self.limbo.get('one'))
        self.assertEqual(id, self.limbo.stored['one'])
    
    def tearDown(self):
        super(Store_PutGet, self).tearDown()


class Store_Delete(StoreDependentTestCase):
    
    def setUp(self):
        super(Store_Delete, self).setUp()
        self.limbo = Limbo()

    def test_deleteOne(self):
        id = self.limbo.put(1, 'one')
        id2 = self.limbo.put(2, 'two')
        self.limbo.delete('one')
        self.assertEqual(1, len(self.limbo.client.list()))
    
    def tearDown(self):
        super(Store_Delete, self).tearDown()

class Store_DeleteThread(StoreDependentTestCase):
    
    def setUp(self):
        super(Store_DeleteThread, self).setUp()
        self.limbo = Limbo()

    def test_deleteOne(self):
        id = self.limbo.put(1, 'one')
        id2 = self.limbo.put(2, 'two')
        #self.mp = Process(target=self.limbo.delete, args=('one',))
        #self.mp.start()
        #self.mp.join()
        self.limbo.delete('one')
        self.assertEqual(1, len(self.limbo.client.list()))
    
    def tearDown(self):
        super(Store_DeleteThread, self).tearDown()