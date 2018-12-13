import time
from nexus.store import Limbo

import logging; logger = logging.getLogger(__name__)

class Visual():
    '''Class for displaying data
    '''

    def __init__(self, name, client):
        self.name = name
        self.client = client
