import os
import yaml
import io
from inspect import signature
from importlib import import_module

import logging; logger = logging.getLogger(__name__)

#TODO: Write a save function for Tweak objects output as YAML configFile but using TweakModule objects

class RepeatedActorError(Exception):
    pass

class Tweak():
    ''' Handles configuration and logs of configs for
        the entire server/processing pipeline.
    '''

    def __init__(self, configFile=None):
        cwd = os.getcwd()
        if configFile is None:
            # Going with default config
            self.configFile = cwd+'/basic_demo.yaml'
        else:
            # Reading config from other yaml file
            self.configFile = cwd+'/'+configFile
        
        self.actors = {}
        self.connections = {}
        self.hasGUI = False
        
    def createConfig(self):
        ''' Read yaml config file and create config for Nexus
            TODO: check for config file compliance, error handle it
        '''
        with open(self.configFile, 'r') as ymlfile:
            cfg = yaml.safe_load(ymlfile)

        for name,actor in cfg['actors'].items(): 
            # put import/name info in TweakModule object TODO: make ordered?

            if name in self.actors.keys():
                raise RepeatedActorError

            packagename = actor.pop('package')
            classname = actor.pop('class')
            
            try:
                __import__(packagename, fromlist=[classname])

            except ModuleNotFoundError:
                logger.error('Error: Packagename not valid')

            except ImportError:
                logger.error('Error: Classname not valid within package')

            mod = import_module(packagename)
            clss = getattr(mod, classname)
            sig= signature(clss)
            tweakModule = TweakModule(name, packagename, classname, options=actor)
            try:
                sig.bind(tweakModule.options)
            except TypeError as e:
                logger.error('Error: Invalid arguments passed')

            if "GUI" in name:
                self.hasGUI = True
                self.gui = tweakModule
            
            else:
                self.actors.update({name:tweakModule})
                
        for name,conn in cfg['connections'].items():
            #TODO check for correctness  TODO: make more generic (not just q_out)
            self.connections.update({name:conn}) #conn should be a list
        

    def addParams(self, type, param):
        ''' Function to add paramter param of type type
        '''

    def saveConfig(self):
        #remake cfg TODO
        cfg = self.actors
        yaml.safe_dump(cfg)

class TweakModule():
    def __init__(self, name, packagename, classname, options=None):
        self.name = name
        self.packagename = packagename
        self.classname = classname
        self.options = options

if __name__ == '__main__':

    tweak= Tweak()
    tweak.createConfig()
    print(tweak.actors)