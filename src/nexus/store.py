import time
import numpy as np
import pickle
import pyarrow as arrow
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


class Limbo(StoreInterface):
    ''' Basic interface for our specific data store
        implemented with apache arrow plasma
        Objects are stored with object_ids
        References to objects are contained in a dict where key is
          shortname, value is object_id
    '''

    def __init__(self, name='default', store_loc='/tmp/store'):
        self.name = name
        self.client = self.connectStore(store_loc)
        self.stored = {}
    
    
    def connectStore(self, store_loc):
        ''' Connect to the store at store_loc
            Raises exception if can't connect
            Returns the plamaclient if successful
        '''
        
        try:
            client = plasma.connect(store_loc, '', 0)
            logger.info('Successfully connected to store')
        except Exception as e:
            #client = None
            logger.exception('Cannot connect to store: {0}'.format(e))
            raise Exception
        return client


    def put(self, object, object_name):
        ''' Put a single object referenced by its string name 
            into the store
            Unknown errors 
        '''
        
        id = self.client.put(object)
        self.stored.update({object_name:id})
        logger.info('object ', object_name, 'successfully stored')
        return id  #needed?
    
    
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
            raise Exception

        return self.put(buf, data_name)


    def updateStored(self, object_name, object_id):
        '''Update local dict with info we need locally
        '''
    
        self.stored.update({object_name:id})
    
    
    def get(self, object_name):
        ''' Get a single object from the store
            Checks to see if it knows the object first
            Otherwise throw CannotGetObject to request dict update
            TODO: update for lists of objects
        '''
        
        if self.stored.get(object_name) is None:
            logger.error('Never recorded storing this object: ', object_name)
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
        res = self.client.get(self.stored.get(object_name), 0)
        # Can also use contains() to check
        if isinstance(res, ObjectNotAvailable):
            logger.warn('Object ',object_name,' cannot be found.')
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
            logger.error('Never recorded storing this object: ', object_name)
            # Don't know anything about this object, treat as problematic
            raise CannotGetObjectError
        else:
            self._delete(object_name)
            
    
    def _delete(self, object_name):
        ''' Deletes object from store
        '''
        self.client.delete([self.stored.get(object_name)])
        #redo with object_id as argument


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


