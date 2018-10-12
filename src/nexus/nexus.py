import time
import subprocess
from multiprocessing import Pool
import numpy as np
import pyarrow as arrow
import pyarrow.plasma as plasma
import .store
from ..visual import Visual
from ..process import Processor
from ..acquire import Acquirer

import logging; logger = logging.getLogger(__name__)

class Nexus(object):
''' Main server class for handling objects in RASP

'''

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def loadTweak(self, file=None):
        self.tweak = Tweak(file)

    def createNexus(self):
        self.limbo = store.Limbo()
        self.loadTweak()
    
        self.visName = Tweak.visName
        self.Visual = Visual(self.visName)

        self.procName = Tweak.procName
        self.Processor = Processor(self.procName)

        self.acqName = Tweak.acqName
        self.Acquirer = Acquirer(self.acqName)

    def destroyNexus(self):
        self.limbo.closeStore()


if __name__ == '__main__':
    testNexus = Nexus('test')
    testNexus.createNexus()
    testNexus.destroyNexus()
    
    
    
    