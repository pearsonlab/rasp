import time

import logging; logger = logging.getLogger(__name__)

class Acquirer():
    '''Class for acquiring images
    '''

    def __init__(self, name, client):
        self.name = name
        self.client = client


