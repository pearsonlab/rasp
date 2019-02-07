import time
import numpy as np
import cv2
from nexus.store import Limbo
from scipy.spatial.distance import cdist
from math import floor

import logging; logger = logging.getLogger(__name__)

class Visual():
    '''Abstract lass for displaying data
    '''
    def plotEstimates(self):
        ''' Always need to plot some kind of estimates
        '''
        raise NotImplementedError


class CaimanVisual(Visual):
    ''' Class for displaying data from caiman processor
    '''

    def __init__(self, name, client):
        self.name = name
        self.client = client
        self.plots = [0,1,2]
        self.com1 = np.zeros(2)
        self.com2 = np.zeros(2)
        self.com3 = np.zeros(2)
        self.neurons = []
        self.estsAvg = []

    def plotEstimates(self, ests, frame_number):
        ''' Take numpy estimates and t=frame_number
            Create X and Y for plotting, return
        '''
        #print('before')
        avg = self.runAvg(ests)[self.plots[0]]
        #print('after')

        if frame_number >= 200:
            # TODO: change to init batch here
            window = 200
        else:
            window = frame_number

        if ests.shape[1]>0:
            #print(ests.shape)
            #print(ests[:,frame_number-window:frame_number])
            Yavg = np.mean(ests[:,frame_number-window:frame_number], axis=0) 
            #print('Yavg: ', Yavg)
            #Y0 = ests[self.plots[0],frame_number-window:frame_number]
            Y1 = ests[self.plots[0],frame_number-window:frame_number]
            #print('Y1', Y1)
            X = np.arange(0,Y1.size)+(frame_number-window)
            #print('X', X)
            return X,[Y1,Yavg],avg

    def runAvg(self, ests):
        estsAvg = []
        # TODO: this goes in another class
        for i in range(ests.shape[0]):
            tmpList = []
            for j in range(int(np.floor(ests.shape[1]/100))+1):
                tmp = np.mean(ests[int(i)][int(j)*100:int(j)*100+100])
                tmpList.append(tmp)
            estsAvg.append(tmpList)
        self.estsAvg = np.array(estsAvg)
        return self.estsAvg


    def selectNeurons(self, x, y, coords):
        ''' x and y are coordinates
            identifies which neuron is closest to this point
            and updates plotEstimates to use that neuron
            TODO: pick a subgraph (0-2) to plot that neuron (input)
                ie, self.plots[0] = new_ind for ests
        '''
        neurons = [o['neuron_id']-1 for o in coords]
        com = np.array([o['CoM'] for o in coords])
        dist = cdist(com, [np.array([y, x])])
        if np.min(dist) < 50:
            selected = neurons[np.argmin(dist)]
            self.plots[0] = selected
            self.com1 = com[selected] #np.array([com[selected][1], com[selected][0]])
        else:
            logger.info('No neurons nearby where you clicked')
            self.com1 = com[0]

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
        newNeur = None
        if len(self.neurons) < len(coords):
            #print('adding ', len(coords)-len(self.neurons), ' neurons')
            newNeur = [o['CoM'] for o in coords[len(self.neurons):]]
            self.neurons.extend(newNeur)
        return newNeur
