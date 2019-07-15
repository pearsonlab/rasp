import time
import sys
import lmdb
import numpy as np
import pickle
import pyarrow as arrow
from pyarrow import PlasmaObjectExists
import pyarrow.plasma as plasma
from pyarrow.plasma import ObjectNotAvailable
from pyarrow.lib import ArrowIOError
import subprocess
from multiprocessing import Pool
from concurrent.futures import ThreadPoolExecutor
from queue import Empty
from nexus.module import Spike
from scipy.sparse import csc_matrix

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
                 use_hdd=False, hdd_maxstore=1e10, hdd_path='output/', flush_immediately=False,
                 commit_freq=20):

        """
        Constructor for the Limbo

        :param name:
        :param store_loc: Apache Arrow Plasma client location
        :param use_hdd: bool Also write data to disk using the LMDB

        :param hdd_maxstore:
            Maximum size database may grow to; used to size the memory mapping.
            If the database grows larger than map_size, a MapFullError will be raised.
            On 64-bit there is no penalty for making this huge. Must be <2GB on 32-bit.

        :param hdd_path: Path to LMDB folder.
        :param flush_immediately: Save objects to disk immediately
        :param commit_freq: If not flush_immediately, flush data to disk every _ puts.
        """

        self.name = name
        self.store_loc = store_loc
        self.client = self.connectStore(store_loc)
        self.stored = {} # Dict of all objects

        # Offline db
        self.use_hdd = use_hdd
        self.flush_immediately = flush_immediately

        if use_hdd:
            if not isinstance(hdd_path, str):
                raise ValueError('Invalid disk file path.')

            filename = f'/lmdb'  # {datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}'

            self.lmdb_env = lmdb.open(hdd_path + filename, map_size=hdd_maxstore, sync=flush_immediately)
            self.lmdb_commit_freq = commit_freq
            self.lmdb_put_cache = {}
            self.lmdb_obj_id_to_key = {}

    def reset(self):
        ''' Reset client connection
        '''
        self.client = self.connectStore(self.store_loc)
        logger.debug('Reset local connection to store')

    def release(self):
        self.client.disconnect()

    def flush(self):
        """ Must run before exiting. Flushes buffer to disk. """
        if self.use_hdd:
            self.lmdb_env.sync()
            self.lmdb_env.close()
            print('Flushed!')

    def connectStore(self, store_loc):
        ''' Connect to the store at store_loc
            Raises exception if can't connect
            Returns the plamaclient if successful
            Updates the client internal
        '''
        try:
            #self.client = plasma.connect(store_loc)
            self.client: plasma.PlasmaClient = plasma.connect(store_loc, '', 0)
            logger.info('Successfully connected to store')
        except Exception as e:
            logger.exception('Cannot connect to store: {0}'.format(e))
            raise Exception
        return self.client

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

    def put(self, obj, object_name, flush_this_immediately=False):
        """
        Put a single object referenced by its string name
        into the store
        Raises PlasmaObjectExists if we are overwriting
        Unknown error

        :param obj:
        :param object_name:
        :type object_name: str
        :param flush_this_immediately:
        :return: Plasma object ID
        :rtype: class 'plasma.ObjectID'
        """
        object_id = None

        try:
            # Need to pickle if object is csc_matrix
            if isinstance(obj, csc_matrix):
                object_id = self.client.put(pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL))
            else:
                object_id = self.client.put(obj)

            self.updateStored(object_name, object_id)

            if self.use_hdd:
                self._lmdb_helper(obj, object_id, object_name, flush_this_immediately=flush_this_immediately)

        except PlasmaObjectExists:
            logger.error('Object already exists. Meant to call replace?')
            #raise PlasmaObjectExists

        except ArrowIOError as e:
            logger.error('Could not store object '+object_name+': {} {}'.format(type(e).__name__, e))
            logger.info('Refreshing connection and continuing')
            self.reset()

        except Exception as e:
            logger.error('Could not store object '+object_name+': {} {}'.format(type(e).__name__, e))

        return object_id

    def _lmdb_helper(self, obj, obj_id, object_name, flush_this_immediately):
        """
        LMDB interface

        :param obj: Object to be saved
        :param obj_id: Object_id from Plasma client
        :type obj_id: class 'plasma.ObjectID'
        :param object_name:
        :param flush_this_immediately: Override self.flush_immediately. For storage of critical objects.

        :return: None
        """
        put_key: bytes = b''.join([object_name.encode(), pickle.dumps(time.time())])

        self.lmdb_obj_id_to_key[obj_id] = put_key
        self.lmdb_put_cache[put_key] = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)

        if len(self.lmdb_put_cache) > self.lmdb_commit_freq or (self.flush_immediately or flush_this_immediately):
            with self.lmdb_env.begin(write=True) as txn:
                for key, value in self.lmdb_put_cache.items():
                    txn.put(key, value, overwrite=True)

            self.lmdb_put_cache = {}

            if flush_this_immediately:
                self.lmdb_env.sync()

    def _put(self, obj, object_id):
        return self.client.put(obj, object_id)
    
    def replace(self, object, object_name):
        ''' Explicitly replace an object with new data
            TODO: Combine with put. Default behavior:
                Accept overwrite, but dump old data to disk and log.
            Throws AssertionError if replace fails
        '''

        # Check/confirm we need to replace
        if object_name in self.stored:
            logger.debug('replacing '+object_name)
            #self.saveSubstore(object_name) #TODO
            old_id = self.stored[object_name]
            self.delete(object_name)
          #  newconn = plasma.connect('/tmp/store', '', 0)
           # object_id = newconn.put(object, old_id)
           # newconn.disconnect()
            object_id = self.client.put(object, old_id) #plasma put
            self.updateStored(object_name, object_id)
            assert object_id == old_id

        else:
            logger.error('Not replacing '+object_name)
            object_id = self.client.put(object) #internal put fcn
            self.updateStored(object_name, object_id)
        
        return object_id

    def putArray(self, data):
        ''' General put for numpy array objects into the store
            TODO: add pandas?
            Unknown errors
        '''
        buf = arrow.serialize(data).to_buffer()


    def _getArray(self, buf):
        return arrow.deserialize(buf)


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


    def get(self, object_name):
        ''' Get a single object from the store
            Checks to see if it knows the object first
            Otherwise throw CannotGetObject to request dict update
            TODO: update for lists of objects
        '''
        #print('trying to get ', object_name)
        if self.stored.get(object_name) is None:
            logger.error('Never recorded storing this object: '+object_name)
            # Don't know anything about this object, treat as problematic
            raise CannotGetObjectError
        else:
            return self._get(object_name)


    def get_all(self):
        ''' Get a listing of all objects in the store
        '''
        return self.client.list()


    def _get(self, object_name):
        ''' Get an object from the store using its name
            Assumes we know the id for the object_name
            Raises ObjectNotFound if object_id returns no object from the store
        '''
        res = self.getID(self.stored.get(object_name))
        # Can also use contains() to check
        if isinstance(res, ObjectNotAvailable):
            logger.warning('Object {} cannot be found.'.format(object_name))
            raise ObjectNotFoundError
        elif isinstance(res, arrow.lib.Buffer):
            logger.info('Deserializing first')
            return self._getArray(res)
        else:
            return res

    def getID(self, obj_id, hdd_only=False):

        # Check in RAM
        if not hdd_only:
            res = self.client.get(obj_id, 0)  # Timeout = 0 ms
            if res is not plasma.ObjectNotAvailable:
                # Deal with pickled objects.
                if isinstance(res, bytes):
                    return pickle.loads(res)
                else:
                    return res

        # Check in disk
        if self.use_hdd:
            with self.lmdb_env.begin() as txn:
                get_key = self.lmdb_obj_id_to_key[obj_id]
                res = pickle.loads(txn.get(get_key))

            if res is not None:
                return res

        logger.warning('Object {} cannot be found.'.format(obj_id))
        raise ObjectNotFoundError

    def getList(self, ids):
        return [self.getID(i) for i in ids]  # self.client.get(ids) # Need to replace to enable LMDB

    def deleteName(self, object_name):
        ''' Deletes an object from the store based on name
            assumes we have id from name
            This prevents us from deleting other portions of 
            the store that we don't have access to
        '''

        if self.stored.get(object_name) is None:
            logger.error('Never recorded storing this object: '+object_name)
            # Don't know anything about this object, treat as problematic
            raise CannotGetObjectError
        else:
            retcode = self._delete(object_name)
            self.stored.pop(object_name)
            
    def delete(self, id):
        try:
            self.client.delete([id])
        except Exception as e:
            logger.error('Couldnt delete: {}'.format(e))
    
    def _delete(self, object_name):
        ''' Deletes object from store
        '''
        tmp_id = self.stored.get(object_name)

        new_client = plasma.connect('/tmp/store', '', 0)
        new_client.delete([tmp_id])
        new_client.disconnect()

    def saveStore(self, fileName='/home/store_dump'):
        ''' Save the entire store to disk
            Uses pickle, should extend to mmap, hd5f, ...
        '''
        raise NotImplementedError

    def saveTweak(self, tweak_ids, fileName='/home/tweak_dump'):
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

    def saveSubstore(self, keys, fileName='/home/substore_dump'):
        ''' Save portion of store based on keys
            to disk
        '''
        raise NotImplementedError

class HStore(StoreInterface):
    ''' Implementation of the data store on disk.
        Using dict-like structure, employs h5py via hickle
    '''

    def __init__(self):
        ''' Construct the initial store.
        '''
        pass

    def get(self):
        pass

    def put(self):
        pass

    def delete(self):
        pass

    def replace(self):
        pass

    def subscribe(self):
        pass


def saveObj(obj, name):
    with open('/media/hawkwings/Ext Hard Drive/dump/dump'+str(name)+'.pkl', 'wb') as output:
        pickle.dump(obj, output)

#class LStore(StoreInterface):
#   ''' Implement data store using LMDB in python. TODO?
#   '''


class ObjectNotFoundError(Exception):
    pass


class CannotGetObjectError(Exception):
    pass


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
