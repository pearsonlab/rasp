import time
import sys
import numpy as np
import pickle
import pyarrow as arrow
from pyarrow import PlasmaObjectExists
import pyarrow.plasma as plasma
from pyarrow.plasma import ObjectNotAvailable
import subprocess
from multiprocessing import Pool

import logging; logger=logging.getLogger(__name__)


class StoreInterface():
    '''General interface for a store
    '''
    def get(self):
        raise NotImplementedError

    def put(self):
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

    def __init__(self, name='default', store_loc='/tmp/store'):
        self.name = name
        self.store_loc = store_loc
        self.client = self.connectStore(store_loc)
        self.stored = {}
    
    def reset(self):
        ''' Reset client connection
        '''
        self.client = self.connectStore(self.store_loc)

    def connectStore(self, store_loc):
        ''' Connect to the store at store_loc
            Raises exception if can't connect
            Returns the plamaclient if successful
            Updates the client internal
        '''
        
        try:
            self.client = plasma.connect(store_loc, '', 0)
            logger.info('Successfully connected to store')
        except Exception as e:
            #client = None
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


    def put(self, object, object_name):
        ''' Put a single object referenced by its string name 
            into the store
            Raises PlasmaObjectExists if we are overwriting
            Unknown error
        '''
        object_id = None
        try:
            object_id = self.client.put(object)
            #print('we did a plasma put in put ', object_id)
                #self.stored.update({object_name:object_id})
            self.updateStored(object_name, object_id)
            logger.error('object successfully stored: '+object_name)
            #print(object_id)
        except PlasmaObjectExists:
            logger.error('Object already exists. Meant to call replace?')
            print(self.client.list())
            print(self.stored.keys())
            #raise PlasmaObjectExists
        except Exception as e:
            logger.error('could not store object: {0}'.format(e))
            print('size ', sys.getsizeof(object))
        return object_id
    
    
    def replace(self, object, object_name):
        ''' Explicitly replace an object with new data
            TODO: Combine with put. Default behavior:
                Accept overwrite, but dump old data to disk and log.
            Throws AssertionError if replace fails
        '''

        # Check/confirm we need to replace
        if object_name in self.stored:
            logger.info('replacing '+object_name)
            self.saveSubstore(object_name)
            old_id = self.stored[object_name]
            self.delete(object_name)
            #print('before newconn')
          #  newconn = plasma.connect('/tmp/store', '', 0)
            #print('got newconn ', newconn)
           # object_id = newconn.put(object, old_id)
            #print('put using newconn; end of replacing')
           # newconn.disconnect()
            object_id = self.client.put(object, old_id) #plasma put
            self.updateStored(object_name, object_id)
            assert object_id == old_id

        else:
            logger.error('Not replacing '+object_name)
            object_id = self.client.put(object) #internal put fcn
            self.updateStored(object_name, object_id)
        
        return object_id

#    def putArray(self, data, size=1000):
#        ''' General put for numpy array objects into the store
#            TODO: use pandas
#            Unknown errors
#        '''
#    
#        arr = arrow.array(data)
#        id = plasma.ObjectID(np.random.bytes(20))
#        buf = memoryview(self.client.create(id, size))

    
    def putBuffer(self, data, data_name):
        ''' Try to serialize the data to store as buffer
            TODO: convert unknown data types to dicts for serializing
                using SerializationContext
            TODO: consider to_components for large np arrays
            Unknown errors
            
            doc: arrow.apache.org/docs/python/ipc.html Arbitrary Object Serialization
        '''
    
        try:
            buf = arrow.serialize(data).to_buffer()
        except Exception as e:
            logger.error('Error: {}'.format(e))
            raise Exception

        return self.put(buf, data_name)


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
        #print('stored? ', self.stored.get(object_name))
        if self.stored.get(object_name) is None:
            logger.error('stored contains: '+self.stored.items())
            logger.error('Never recorded storing this object: '+object_name)
            # Don't know anything about this object, treat as problematic
            raise CannotGetObjectError
        else:
            return self._get(object_name)


    def get_all(self):
        ''' Get a listing of all objects in the store
        '''
        print(self.client.list())
        return self.client.list()


    def _get(self, object_name):
        ''' Get an object from the store using its name
            Assumes we know the id for the object_name
            Raises ObjectNotFound if object_id returns no object from the store
        '''
        #print('trying to get object, ', object_name)
        res = self.client.get(self.stored.get(object_name), 0)
        # Can also use contains() to check
        if isinstance(res, ObjectNotAvailable):
            logger.warn('Object {} cannot be found.'.format(object_name))
            raise ObjectNotFoundError
        else:
            return res


    def delete(self, object_name):
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
            #print('trying to delete ', object_name, ' ID ', self.stored.get(object_name))
            #print(self.client.list())
            retcode = self._delete(object_name)
            #print('supposedly deleted. Retcode: ', retcode)
            #print(self.client.list())
            self.stored.pop(object_name)
            #print('stored has ', self.stored.items())
            #print('DS has ', self.client.list())
            
    
    def _delete(self, object_name):
        ''' Deletes object from store
        '''
        #print('length ', len(self.client.list()))
        #print('list ', self.client.list())
        #print('id to delete is : ', self.stored.get(object_name))
        tmp_id = self.stored.get(object_name)
        #print('tmp id  is ', tmp_id)
        #print(self.client.list())
        #print('before connect to delete')
        new_client = plasma.connect('/tmp/store', '', 0)
        new_client.delete([tmp_id])
        #self.client.delete([tmp_id])
        new_client.disconnect()
        #print('before check store')
        #print('store still there? ', plasma.connect('/tmp/store', '', 0))
        #print('after delete and disconnect')
        #print(self.client.list())
        #print('check temp too: ', new_client.list())
        #redo with object_id as argument?


    def saveStore(self, fileName='/home/store_dump'):
        ''' Save the entire store to disk
            Uses pickle, should extend to mmap, hd5f, ...
        '''


    def saveTweak(self, tweak_ids, fileName='/home/tweak_dump'):
        ''' Save current Tweak object containing parameters
            to run the experiment.
            Tweak is pickleable
            TODO: move this to Nexus' domain?
        '''
        #tweakids list of Tweak items stored. Tweak is list of results
        tweak = self.client.get(tweak_ids)
        #for object ID in list of items in tweak, get from store
        #and put into dict (?)
        with open(fileName, 'wb') as output:
            pickle.dump(tweak, output, -1)


    def saveSubstore(self, keys, fileName='/home/substore_dump'):
        ''' Save portion of store based on keys
            to disk
        '''
        pass



class HardDisk(StoreInterface):
    ''' Implementation of the data store on disk
        instead of in memory. Uses h5 format primarily
    '''

    def __init__(self, folder_loc):
        ''' Construct the hard disk data store
            folder_loc is the location to store data
        '''
        # will likely need multiple formats supported
        pass

    def get(self):
        pass

    def put(self):
        pass



class ObjectNotFoundError(Exception):
    pass

class CannotGetObjectError(Exception):
    pass


