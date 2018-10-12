import time

import logging; logger = logging.getLogger(__name__)

class Visual(object):

    def __init__(self, type):
        self.type = type

    def createVisual(self, type):
        raise NotImplementedError
