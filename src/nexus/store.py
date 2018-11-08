import time
import numpy as np
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

    def __init__(self, store_loc='/tmp/store'):
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
        res = self.client.get(self.stored.get(object_name))
        if isinstance(res, ObjectNotAvailable):
            logger.warn('Object ',object_name,' cannot be found.')
            raise ObjectNotFoundError
        else:
            return res


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


if __name__ == '__main__':
# assumes store server is started
    limbo = Limbo('/tmp/store')
    limbo.put('hi', 'hi_name')
    print(limbo.get('hi_name'))
    #limbo.closeStore()



