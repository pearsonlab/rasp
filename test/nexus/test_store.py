
from unittest import TestCase
from test.test_utils import StoreDependentTestCase
from src.nexus.store import Limbo
from multiprocessing import Process
from pyarrow import PlasmaObjectExists
from scipy.sparse import csc_matrix
import numpy as np
import pyarrow.plasma as plasma
from pyarrow.lib import ArrowIOError
from nexus.store import ObjectNotFoundError
from nexus.store import CannotGetObjectError
import pickle

#TODO: assertRaises doesn't work to check for custom Exceptions

class Limbo_Connect(StoreDependentTestCase):

    def setUp(self):
        super(Limbo_Connect, self).setUp()
        self.limbo = Limbo()

    def test_Connect(self):
        store_loc='/tmp/store'
        self.limbo.connectStore(store_loc)
        self.assertIsInstance(self.limbo.client, plasma.PlasmaClient)

    def test_fail(self):
        store_loc= 'asdf'
        with self.assertRaises((ArrowIOError, Exception)):
            self.limbo.connectStore(store_loc)

    def tearDown(self):
        super(Limbo_Connect, self).tearDown()

class Limbo_Get(StoreDependentTestCase):

    def setUp(self):
        super(Limbo_Get, self).setUp()
        self.limbo = Limbo()

    def test_init_empty(self):
        self.assertFalse(self.limbo.get_all())

    def tearDown(self):
        super(Limbo_Get, self).tearDown()

class Limbo_GetID(StoreDependentTestCase):
    #Check both hdd_only=False/True
    #Check isInstance type, isInstance bytes, else

    def setUp(self):
        super(Limbo_GetID, self).setUp()
        self.limbo=Limbo()

    def test_isMatrix(self): #also tests put matrix
        mat= csc_matrix((3, 4), dtype=np.int8)
        x= self.limbo.put(mat, 'matrix' ) #returns object_id
        self.assertIsInstance(self.limbo.getID(x), csc_matrix)

    def test_notPut(self):
        obj = self.limbo.getID(self.limbo.random_ObjectID(1))
        self.assertRaises(ObjectNotFoundError)

    def UseHDD(self):
        self.lmdb_store.put(1, 'one')
        assertEqual(self.lmdb_store.getID('one', hdd_only=True), 1)

    def tearDown(self):
        super(Limbo_GetID, self).tearDown()

class Limbo_getListandAll(StoreDependentTestCase):
    def setUp(self):
        super(Limbo_getListandAll, self).setUp()
        self.limbo=Limbo()

    def getListandAll(self):
        id = self.limbo.put(1, 'one')
        id2 = self.limbo.put(2, 'two')
        id3 = self.limbo.put(3, 'three')
        self.assertEqual([1, 2], self.limbo.getList(['one', 'two']))
        self.assertEqual([1, 2, 3], self.limbo.get_all())

    def tearDown(self):
        super(Limbo_getListandAll, self).tearDown()

class Limbo_ReleaseReset(StoreDependentTestCase):

    def setUp(self):
        super(Limbo_ReleaseReset, self).setUp()
        self.limbo=Limbo()

    def test_release(self):
        self.limbo.release()
        self.limbo.put(1, 'one')
        self.assertRaises(ArrowIOError)

    def test_reset(self):
        self.limbo.reset()
        self.limbo.put(1, 'one')
        self.assertEqual(self.limbo.get('one'), 1)

    def tearDown(self):
        super(Limbo_ReleaseReset, self).tearDown()

class Limbo_Put(StoreDependentTestCase):

    def setUp(self):
        super(Limbo_Put, self).setUp()
        self.limbo = Limbo()

    def test_putOne(self):
        id = self.limbo.put(1, 'one')
        self.assertEqual(1, self.limbo.get('one'))

    def test_put_twice(self):
        id = self.limbo.put(2, 'two')
        id2 = self.limbo.put(2, 'two')
        self.assertRaises(PlasmaObjectExists)

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

    def test_get_nonexistent(self):
        with self.assertRaises((CannotGetObjectError, Exception)):
            self.limbo.get('three')

    def tearDown(self):
        super(Limbo_PutGet, self).tearDown()


"""class Limbo_Notify(StoreDependentTestCase):
    def setUp(self):
        super(Limbo_Notify, self).setUp()
        self.limbo = Limbo()

    # Add test body here
    def test_notify(self):
        # TODO: not unit testable?


    def tearDown(self):
        super(Limbo_Notify, self).tearDown()"""



class Limbo_UpdateStored(StoreDependentTestCase):
    def setUp(self):
        super(Limbo_UpdateStored, self).setUp()
        self.limbo = Limbo()

    # Accessing self.limbo.stored directly to test getStored separately
    def test_updateGet(self):
        self.limbo.put(1, 'one')
        self.limbo.updateStored('one', 3)
        self.assertEqual(3,self.limbo.stored['one'])

    def tearDown(self):
        super(Limbo_UpdateStored, self).tearDown()

class Limbo_GetStored(StoreDependentTestCase):
    def setUp(self):
        super(Limbo_GetStored, self).setUp()
        self.limbo = Limbo()

    def test_getStoredEmpty(self):
        self.assertFalse(self.limbo.getStored())

    def test_putGetStored(self):
        self.limbo.put(1, 'one')
        self.assertEqual(1, self.limbo.getID(self.limbo.getStored()['one'])) # returns ID

    def tearDown(self):
        super(Limbo_GetStored, self).tearDown()


class Limbo_internalPutGet(StoreDependentTestCase):

    def setUp(self):
        super(Limbo_internalPutGet, self).setUp()
        self.limbo = Limbo()

    def test_put(self):
        id = self.limbo.random_ObjectID(1)
        self.limbo._put(1, id[0])
        self.assertEqual(1, self.limbo.client.get(id[0]))

    def test_get(self):
        id= self.limbo.put(1, 'one')
        self.limbo.updateStored('one', id)
        self.assertEqual(self.limbo._get('one'), 1)

    def test__getNonexistent(self):
        #with self.assertRaises(ObjectNotFoundError): self.limbo._get('three')
        self.assertRaises(Exception, self.limbo._get, 'three' )


    #TODO: write get fail function, same issue as before

    def tearDown(self):
        super(Limbo_internalPutGet, self).tearDown()

class Limbo_saveTweak(StoreDependentTestCase):

    def setUp(self):
        super(Limbo_saveTweak, self).setUp()
        self.limbo = Limbo()

    def test_tweak(self):
        fileName= 'data/tweak_dump'
        id= self.limbo.put(1, 'one')
        id2= self.limbo.put(2, 'two')
        tweak_ids=[id, id2]
        self.limbo.saveTweak(tweak_ids)
        with open(fileName, 'rb') as output:
            self.assertEqual(pickle.load(output), [1, 2])

    def tearDown(self):
        super(Limbo_saveTweak, self).tearDown()
