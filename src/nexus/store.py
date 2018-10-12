import time
import numpy as np
import pyarrow as arrow
import pyarrow.plasma as plasma
from pyarrow.plasma import ObjectNotAvailable
import subprocess
from multiprocessing import Pool

import logging; logger=logging.getLogger(__name__)


class StoreInterface(object):
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

    def __init__(self, size=1*10**9):
        # default store size 1GB
        
        self.startStore(size)
        self.client = self.connectStore()
        self.stored = {}
    
    def startStore(self, size):
        '''
        '''
        
        if size is None:
            raise RuntimeEror('Server size needs to be specified')
        try:
            self.p = subprocess.Popen(['plasma_store',
                              '-s', '/tmp/store',
                              '-m', str(size)],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
            logger.info('Store started successfully')
        except Exception as e:
            logger.exception('Store cannot be started: {0}'.format(e))

    def closeStore(self):
        try:
            self.p.kill()
            logger.info('Store closed successfully')
        except Exception as e:
            logger.exception('Cannot close store {0}'.format(e))
    
    def connectStore(self):
        try:
            client = plasma.connect('/tmp/store', '', 0)
            logger.info('Successfully connected to store')
        except Exception as e:
            client = None
            logger.exception('Cannot connect to store {0}'.format(e))

        return client

    def put(self, object, object_name):
        ''' Put object referenced by its string name into the store
            Unknown errors 
        '''
        
        id = self.client.put(object)
        self.stored.update({object_name:id})
        logger.info('object ', object_name, 'successfully stored')

    def get(self, object_name):
        ''' Get an object from the store using its name
            Raises ObjectNotStored if object_name not linked to object_id
            Raises ObjectNotFound if object_id returns no object from the store
        '''
        
        if self.stored.get(object_name) is None:
            logger.error('Never recorded storing this object: ', object_name)
            raise ObjectNotStoredError
        else:
            res = self.client.get(self.stored.get(object_name))
        if isinstance(res, ObjectNotAvailable):
            logger.warn('For some reason object ',object_name,' was stored but cannot be found.')
            raise ObjectNotFoundError
        else:
            return res


class ObjectNotFoundError(Exception):
    pass

class ObjectNotStoredError(Exception):
    pass
        

if __name__ == '__main__':

    limbo = Limbo()
    limbo.put('hi', 'hi_name')
    print(limbo.get('hi_name'))
    limbo.closeStore()



