import time

import logging; logger = logging.getLogger(__name__)

class Tweak():
    ''' Handles configuration and logs of configs for
        the entire server/processing pipeline.
    '''

    def __init__(self, configFile=None):
        if configFile is None:
            # Going with default config
            self.configFile = '/home' #TODO CHANGEME
        else:
            # Reading config from json file
            self.configFile = configFile

        
        self.visName = {}
        self.procName = {}
        self.acqName = {}

    def addVisual(self, newVisual):
         # newVisual is a visual object, has a name
         self.visName.update({newVisual.name: newVisual})


    def addParams(self, type, param):
        ''' Function to add paramter param of type type
        '''

