import time
import numpy as np
import cv2
from nexus.store import Limbo
from scipy.spatial.distance import cdist
from math import floor

import logging; logger = logging.getLogger(__name__)

class Visual():
    '''Class for displaying data
        TODO: Make specific caiman-type implementation, vs general framework
    '''

    def __init__(self, name, client):
        self.name = name
        self.client = client
        self.plots = [0,1,2]
        self.com1 = np.zeros(2)
        self.com2 = np.zeros(2)
        self.com3 = np.zeros(2)


    def plotEstimates(self, ests, frame_number):
        ''' Take numpy estimates and t=frame_number
            Create X and Y for plotting, return
        '''
        if frame_number >= 300:
            # TODO: change to init batch here
            window = 300
        else:
            window = frame_number

        Y0 = ests[self.plots[0]][frame_number-window:frame_number]
        Y1 = ests[self.plots[1]][frame_number-window:frame_number]
        Y2 = ests[self.plots[2]][frame_number-window:frame_number]
        X = np.arange(0,Y0.size)+(frame_number-window)
        return X,[Y0,Y1,Y2]

    def selectNeurons(self, x, y, coords):
        ''' x and y are coordinates
            identifies which neuron is closest to this point
            and updates plotEstimates to use that neuron
            TODO: pick a subgraph (0-2) to plot that neuron (input)
                ie, self.plots[0] = new_ind for ests
        '''
        print('got here')
        neurons = [o['neuron_id']-1 for o in coords]
        com = np.array([o['CoM'] for o in coords])
        dist = cdist(com, [np.array([x, y])]) #transposed orig image?? FIXME
        if np.min(dist) < 50:
            selected = neurons[np.argmin(dist)]
            self.plots[0] = selected
            self.com1 = com[selected] #np.array([com[selected][1], com[selected][0]])
            print('selected neuron #', selected, ' located at ', self.com1)
        else:
            logger.info('No neurons nearby where you clicked')

    def getSelected(self):
        ''' Returns list of 3 coordinates for plotted selections
        '''
        return [self.com1, self.com2, self.com3]

    def plotRaw(self, img):
        ''' Take img and draw it
            TODO: make more general
        '''
        # if self.com1 is not None and img is not None:
        #     #add colored dot to selected neuron
        #     #print('self.com ', self.com1, 'img shape ', img.shape)
        #     x = floor(self.com1[0])
        #     y = floor(self.com1[1])
        return img

    def plotContours(self, coords):
        ''' Provide contours to plot atop raw image
        '''
        return [o['coordinates'] for o in coords]

    def plotCoM(self, coords):
        ''' Provide contours to plot atop raw image
        '''
        return [o['CoM'] for o in coords]


