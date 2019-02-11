import time
import numpy as np
import cv2
from nexus.store import Limbo
from scipy.spatial.distance import cdist
from math import floor
import colorsys

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
        self.coords = None

    def plotEstimates(self, ests, frame_number):
        ''' Take numpy estimates and t=frame_number
            Create X and Y for plotting, return
        '''
        stim = self.stimAvg(ests)
        avg = stim[self.plots[0]]
        avgAvg = np.array(np.mean(stim, axis=0))

        if frame_number >= 200:
            # TODO: change to init batch here
            window = 200
        else:
            window = frame_number

        if ests.shape[1]>0:
            Yavg = np.mean(ests[:,frame_number-window:frame_number], axis=0) 
            #Y0 = ests[self.plots[0],frame_number-window:frame_number]
            Y1 = ests[self.plots[0],frame_number-window:frame_number]
            X = np.arange(0,Y1.size)+(frame_number-window)
            return X,[Y1,Yavg],avg,avgAvg

    def stimAvg(self, ests):
        ''' For now, avergae over every 100 frames
        where each 100 frames presents a new stimulus
        '''
        estsAvg = []
        # TODO: this goes in another class
        for i in range(ests.shape[0]): #for each component
            tmpList = []
            for j in range(int(np.floor(ests.shape[1]/100))+1): #average over stim window
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

    def getFirstSelect(self):
        first = None
        if self.neurons:
            first = [np.array(self.neurons[0])]
        return first

    def plotRaw(self, img):
        ''' Take img and draw it
            TODO: make more general
        '''
        # if self.com1 is not None and img is not None:
        #     #add colored dot to selected neuron
        #     #print('self.com ', self.com1, 'img shape ', img.shape)
        #     x = floor(self.com1[0])
        #     y = floor(self.com1[1])
        image = img #np.minimum((img*255.),255).astype('u1')
        return image

    def plotCompFrame(self, image, thresh):
        ''' Computes colored frame and nicer background+components frame
        '''
        ###color = np.stack([image, image, image], axis=-1).astype(np.uint8).copy()
        color = np.stack([image, image, image, image], axis=-1)
        image2 = np.stack([image, image, image, image], axis=-1)
        image2[...,3] = 100
        color[...,3] = 255
        if self.coords is not None:
            for i,c in enumerate(self.coords):
                c = np.array(c)
                ind = c[~np.isnan(c).any(axis=1)].astype(int)
                ###cv2.fillConvexPoly(color, ind, (255,0,0))
                color[ind[:,1], ind[:,0], :] = self.tuningColor(i, color[ind[:,1], ind[:,0]])
                image2[ind[:,1], ind[:,0], :] = self.threshNeuron(i, thresh) #(255,255,255,255)
        return np.swapaxes(color,0,1), np.swapaxes(image2,0,1)

    def threshNeuron(self, ind, thresh):
        display = (255,255,255,255)
        if self.estsAvg[ind] is not None:
            intensity = np.max(self.estsAvg[ind])
            #print('thresh ', thresh, ' and inten ', intensity)
            if thresh > intensity: 
                display = (255,255,255,0)
            
        return display

    def tuningColor(self, ind, inten):
        if self.estsAvg[ind] is not None:
            ests = np.array(self.estsAvg[ind])
            h = np.argmax(ests)*36/360
            intensity = 1- np.max(inten[0][0])/255.0
            r, g, b, = colorsys.hls_to_rgb(h, intensity, 0.8)
            r, g, b = [x*255.0 for x in (r, g, b)]
            #print((r, g, b)+ (200,))
            return (r, g, b)+ (intensity*255,)
        else:
            return (255,255,255,0)
        

    def plotContours(self, coords):
        ''' Provide contours to plot atop raw image
        '''
        self.coords = [o['coordinates'] for o in coords]
        return self.coords

    def plotCoM(self, coords):
        ''' Provide contours to plot atop raw image
        '''
        newNeur = None
        if len(self.neurons) < len(coords):
            #print('adding ', len(coords)-len(self.neurons), ' neurons')
            newNeur = [o['CoM'] for o in coords[len(self.neurons):]]
            self.neurons.extend(newNeur)
        return newNeur
