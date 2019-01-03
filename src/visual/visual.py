import time
import numpy as np
import cv2
from nexus.store import Limbo
from caiman.utils.visualization import plot_contours

import logging; logger = logging.getLogger(__name__)

class Visual():
    '''Class for displaying data
        TODO: Make specific caiman-type implementation, vs general framework
    '''

    def __init__(self, name, client):
        self.name = name
        self.client = client

    def plotEstimates(self, ests, frame_number):
        ''' Take numpy estimates and t=frame_number
            Create X and Y for plotting, return
        '''
        if frame_number >= 300:
            # TODO: change to init batch here
            window = 300
        else:
            window = frame_number

        Y0 = ests[0][frame_number-window:frame_number]
        Y1 = ests[1][frame_number-window:frame_number]
        X = np.arange(0,Y0.size)+(frame_number-window)
        return X,[Y0,Y1]

    def plotRaw(self, img):
        ''' Take img and draw it
            TODO: make more general
        '''
        #coords = plot_contours(A, img)
        #cv2.imshow('raw', img)