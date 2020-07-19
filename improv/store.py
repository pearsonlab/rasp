import datetime
import os
import pickle
import time
import numpy as np
import pyarrow as arrow
import pyarrow.plasma as plasma
from pyarrow.plasma import PlasmaObjectExists
from pyarrow.lib import ArrowIOError
from pyarrow.plasma import ObjectNotAvailable
from scipy.sparse import csc_matrix
from improv.actor import Spike
from queue import Empty

import logging; logger=logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

#TODO: Use Apache Arrow for better memory usage with the Plasma store

class StoreInterface():
    '''General interface for a store
    '''
    def get(self):
        raise NotImplementedError

    def put(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError

    def replace(self):
        raise NotImplementedError

    def subscribe(self):
        raise NotImplementedError


class Limbo(StoreInterface):
    ''' Basic interface for our specific data store
        implemented with apache arrow plasma
        Objects are stored with object_ids
        References to objects are contained in a dict where key is
          shortname, value is object_id
    '''

    def __init__(self, name='default', store_loc='/tmp/store',
                 hdd_loc='output/', use_hdd=False, hdd_maxstore=1e12,
                 flush_immediately=False, commit_freq=20):
        # TODO TODO TODO: Refactor to use local hdd settings instead of put and get
        ''' Constructor for Limbo
            store_loc: Apache Arrow Plasma client location, default is /tmp/store
            hdd_loc: Path to LMDB folder if used
            use_hdd: flag to also write data to disk using the LMDB
            hdd_maxstore: Maximum size database may grow to; used to size the memory mapping. see LMDBStore
                TODO: NO errors raised without being handled or suggested resolution
            flush_immediately: Save objects to disk immediately
            commit_freq: If not flush_immediately, flush data to disk every N puts
        '''

        self.name = name
        self.store_loc = store_loc
        self.client = self.connectStore(store_loc)
        self.stored = {}

        # Offline db
        self.use_hdd = use_hdd
        self.flush_immediately = flush_immediately

        if use_hdd:
            self.lmdb_store = LMDBStore(max_size=hdd_maxstore, path=hdd_path, flush_immediately=flush_immediately,
                                        commit_freq=commit_freq, from_limbo=True)

    def connectStore(self, store_loc):
        ''' Connect to the store at store_loc
            Raises exception if can't connect
            Returns the plasmaclient if successful
            Updates the client internal
        '''
        try:
            #self.client = plasma.connect(store_loc)
            self.client: plasma.PlasmaClient = plasma.connect(store_loc, 20)
            logger.info('Successfully connected to store')
        except Exception as e:
            logger.exception('Cannot connect to store: {0}'.format(e))
            raise CannotConnectToStoreError(store_loc)
        return self.client

    def put(self, object, object_name, save=False):
        ''' Put a single object referenced by its string name
            into the store
        '''
        object_id = None
        try:
            # Need to pickle if object is csc_matrix
            if isinstance(object, csc_matrix):
                object_id = self.client.put(pickle.dumps(object, protocol=pickle.HIGHEST_PROTOCOL))
            else:
                object_id = self.client.put(object)
            self.updateStored(object_name, object_id)
            if self.use_hdd:
                self.lmdb_store.put(object, object_name, obj_id=object_id, save=save)
        except PlasmaObjectExists:
            logger.error('Object already exists. Meant to call replace?')
        except ArrowIOError as e:
            logger.error('Could not store object '+object_name+': {} {}'.format(type(e).__name__, e))
            logger.info('Refreshing connection and continuing')
            self.reset()
        except Exception as e:
            logger.error('Could not store object '+object_name+': {} {}'.format(type(e).__name__, e))
        return object_id

    def get(self, object_name):
        ''' Get a single object from the store
            Checks to see if it knows the object first
            Otherwise throw CannotGetObject to request dict update
            TODO: update for lists of objects
            TODO: replace with getID
        '''
        #print('trying to get ', object_name)
        if self.stored.get(object_name) is None:
            logger.error('Never recorded storing this object: '+object_name)
            # Don't know anything about this object, treat as problematic
            raise CannotGetObjectError(query = object_name)
        else:
            return self._get(object_name)

    def getID(self, obj_id, hdd_only=False):
        ''' Preferred mechanism for getting. TODO: Rename
        '''
        # Check in RAM
        if not hdd_only:
            res = self.client.get(obj_id,0)
            if isinstance(res, type):
                logger.warning('Object {} cannot be found.'.format(obj_id))
                raise ObjectNotFoundError(obj_id_or_name = obj_id)
            # Deal with pickled objects.
            elif isinstance(res, bytes): #TODO don't use generic bytes
                return pickle.loads(res)
            else:
                return res

        # Check in disk TODO: rework logic for faster gets
        if self.use_hdd:
            res = self.lmdb_store.get(obj_id)
            if res is not None:
                return res

    def getList(self, ids):
        ''' Get multiple objects from the store
        '''
        return self.client.get(ids)

    def get_all(self):
        ''' Get a listing of all objects in the store
        '''
        return self.client.list()

    def reset(self):
        ''' Reset client connection
        '''
        self.client = self.connectStore(self.store_loc)
        logger.debug('Reset local connection to store')

    def release(self):
        self.client.disconnect()

    def subscribe(self):
        ''' Subscribe to a section? of the ds for singals
            Throws unknown errors
        '''
        try:
            self.client.subscribe()
        except Exception as e:
            logger.error('Unknown error: {}'.format(e))
            raise Exception

    def notify(self):
        try:
            notification_info = self.client.get_next_notification()
            #recv_objid, recv_dsize, recv_msize = notification_info
        except ArrowIOError as e:
            notification_info = None
        except Exception as e:
            logger.exception('Notification error: {}'.format(e))
            raise Exception

        return notification_info

    def random_ObjectID(self, number=1):
        ids = []
        for i in range(number):
            ids.append(plasma.ObjectID(np.random.bytes(20)))
        return ids

    def updateStored(self, object_name, object_id):
        ''' Update local dict with info we need locally
            Report to Nexus that we updated the store
                (did a put or delete/replace)
        '''
        self.stored.update({object_name:object_id})

    def getStored(self):
        ''' returns its info about what it has stored
        '''
        return self.stored

    def _put(self, obj, id):
        ''' Internal put
        '''
        return self.client.put(obj, id)

    def _get(self, object_name):
        ''' Get an object from the store using its name
            Assumes we know the id for the object_name
            Raises ObjectNotFound if object_id returns no object from the store
        '''
        res = self.getID(self.stored.get(object_name))
        # Can also use contains() to check
        logger.warning('{}'.format(object_name))
        if isinstance(res, ObjectNotAvailable):
            logger.warning('Object {} cannot be found.'.format(object_name))
            raise ObjectNotFoundError(obj_id_or_name = object_name) #TODO: Don't raise?
        else:
            return res

    #TODO: Likely remove all this functionality for security.
    # def deleteName(self, object_name):
    #     ''' Deletes an object from the store based on name
    #         assumes we have id from name
    #         This prevents us from deleting other portions of
    #         the store that we don't have access to
    #     '''

    #     if self.stored.get(object_name) is None:
    #         logger.error('Never recorded storing this object: '+object_name)
    #         # Don't know anything about this object, treat as problematic
    #         raise CannotGetObjectError
    #     else:
    #         retcode = self._delete(object_name)
    #         self.stored.pop(object_name)

    # def delete(self, id):
    #     try:
    #         self.client.delete([id])
    #     except Exception as e:
    #         logger.error('Couldnt delete: {}'.format(e))

    def saveStore(self, fileName='data/store_dump'):
        ''' Save the entire store to disk
            Uses pickle, should extend to mmap, hd5f, ...
        '''
        raise NotImplementedError

    def saveTweak(self, tweak_ids, fileName='data/tweak_dump'):
        ''' Save current Tweak object containing parameters
            to run the experiment.
            Tweak is pickleable
            TODO: move this to Nexus' domain?
        '''
        tweak = self.client.get(tweak_ids)
        #for object ID in list of items in tweak, get from store
        #and put into dict (?)
        with open(fileName, 'wb') as output:
            pickle.dump(tweak, output, -1)

    def saveSubstore(self, keys, fileName='data/substore_dump'):
        ''' Save portion of store based on keys
            to disk
        '''
        raise NotImplementedError


class LMDBStore(StoreInterface):

    def __init__(self, path='output/', name=None, max_size=1e12,
                 flush_immediately=False, commit_freq=20, from_limbo=False):
        '''
        Constructor for LMDB store
        path: Path to LMDB folder.
        name: Name of LMDB. Default to lmdb_[current time in human format].
        max_size:
            Maximum size database may grow to; used to size the memory mapping.
            If the database grows larger than map_size, a MapFullError will be raised.
            On 64-bit there is no penalty for making this huge. Must be <2GB on 32-bit.
        flush_immediately: Save objects to disk immediately
        commit_freq: If not flush_immediately, flush data to disk every _ puts.
        from_limbo: If instantiated from Limbo. Enables object ID functionality.
        '''

        import lmdb

        if name is None:
            name = f'/lmdb_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}'

        if not os.path.exists(path):
            raise FileNotFoundError('Folder to LMDB must exist. Run $mkdir [path].')

        if os.path.exists(path + name):
            raise FileExistsError('LMDB of the same name already exists.')

        self.flush_immediately = flush_immediately
        self.lmdb_env = lmdb.open(path + name, map_size=max_size, sync=flush_immediately)
        self.lmdb_commit_freq = commit_freq
        self.lmdb_obj_id_to_key = {}  # Can be name or key, depending on from_limbo
        self.lmdb_put_cache = {}
        self.from_limbo = from_limbo

    def get(self, obj_name_or_id):
        ''' Get object from object name (!from_limbo) or ID (from_limbo).
            Return None if object is not found.
        '''

        with self.lmdb_env.begin() as txn:
            get_key = self.lmdb_obj_id_to_key[obj_name_or_id]
            r = txn.get(get_key)
            if r is not None:
                return pickle.loads(r)
            else:
                return None

    def put(self, obj, obj_name, obj_id=None, save=False):
        '''
        Put object ID / object pair into LMDB.
        obj: Object to be saved
        save: For storage of critical objects.
        '''

        put_key: bytes = b''.join([obj_name.encode(), pickle.dumps(time.time())])

        if self.from_limbo:
            self.lmdb_obj_id_to_key[obj_id] = put_key
        else:
            self.lmdb_obj_id_to_key[obj_name] = put_key

        self.lmdb_put_cache[put_key] = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)

        if len(self.lmdb_put_cache) > self.lmdb_commit_freq or (self.flush_immediately or save):
            with self.lmdb_env.begin(write=True) as txn:
                for key, value in self.lmdb_put_cache.items():
                    txn.put(key, value, overwrite=True)

            self.lmdb_put_cache = {}

            if save:
                self.lmdb_env.sync()

    def delete(self, obj_id):
        ''' Delete object from LMDB.
        '''
        with self.lmdb_env.begin(write=True) as txn:
            out = txn.pop(self.lmdb_obj_id_to_key[obj_id])
        if out is None:
            raise ObjectNotFoundError(obj_id_or_name = obj_id)

    def flush(self):
        ''' Must run before exiting.
            Flushes buffer to disk.
        '''
        self.lmdb_env.sync()
        self.lmdb_env.close()
        print('Flushed!')

    def replace(self): pass #TODO

    def subscribe(self): pass #TODO


def saveObj(obj, name):
    with open('/media/hawkwings/Ext Hard Drive/dump/dump'+str(name)+'.pkl', 'wb') as output:
        pickle.dump(obj, output)


class ObjectNotFoundError(Exception):

    def __init__(self, obj_id_or_name):

        super().__init__()

        self.name = 'ObjectNotFoundError'
        self.obj_id_or_name = obj_id_or_name

        # TODO: self.message does not properly receive obj_id_or_name
        self.message = 'Cannnot find object with ID/name "{}"'.format(obj_id_or_name)

    def __str__(self):
        return self.message

class CannotGetObjectError(Exception):

    def __init__(self, query):

        super().__init__()

        self.name = 'CannotGetObjectError'
        self.query = query
        self.message = 'Cannot get object {}'.format(self.query)

    def __str__(self):
        return self.message

class CannotConnectToStoreError(Exception):
    '''Raised when failing to connect to store.
    '''
    def __init__(self, store_loc):

        super().__init__()

        self.name = 'CannotConnectToStoreError'

        self.message = 'Cannot connect to store at {}'.format(str(store_loc))

    def __str__(self):
        return self.message

class Watcher():
    ''' Monitors the store as separate process
        TODO: Facilitate Watcher being used in multiple processes (shared list)
    '''
    def __init__(self, name, client):
        self.name = name
        self.client = client
        self.flag = False
        self.saved_ids = []

        self.client.subscribe()
        self.n = 0

    def setLinks(self, links):
        self.q_sig = links

    def run(self):
        while True:
            if self.flag:
                try:
                    self.checkStore2()
                except Exception as e:
                    logger.error('Watcher exception during run: {}'.format(e))
                    #break
            try:
                signal = self.q_sig.get(timeout=0.005)
                if signal == Spike.run():
                    self.flag = True
                    logger.warning('Received run signal, begin running')
                elif signal == Spike.quit():
                    logger.warning('Received quit signal, aborting')
                    break
                elif signal == Spike.pause():
                    logger.warning('Received pause signal, pending...')
                    self.flag = False
                elif signal == Spike.resume(): #currently treat as same as run
                    logger.warning('Received resume signal, resuming')
                    self.flag = True
            except Empty as e:
                pass #no signal from Nexus

    # def checkStore(self):
    #     notification_info = self.client.notify()
    #     recv_objid, recv_dsize, recv_msize = notification_info
    #     obj = self.client.getID(recv_objid)
    #     try:
    #         self.saveObj(obj)
    #         self.n += 1
    #     except Exception as e:
    #         logger.error('Watcher error: {}'.format(e))

    def saveObj(self, obj, name):
        with open('/media/hawkwings/Ext Hard Drive/dump/dump'+name+'.pkl', 'wb') as output:
            pickle.dump(obj, output)

    def checkStore2(self):
        objs = list(self.client.get_all().keys())
        ids_to_save = list(set(objs) - set(self.saved_ids))

        # with Pool() as pool:
        #     saved_ids = pool.map(saveObjbyID, ids_to_save)
        # print('Saved :', len(saved_ids))
        # self.saved_ids.extend(saved_ids)

        for id in ids_to_save:
            self.saveObj(self.client.getID(id), str(id))
            self.saved_ids.append(id)

# def saveObjbyID(id):
#     client = plasma.connect('/tmp/store')
#     obj = client.get(id)
#     with open('/media/hawkwings/Ext\ Hard\ Drive/dump/dump'+str(id)+'.pkl', 'wb') as output:
#         pickle.dump(obj, output)
#     return id
