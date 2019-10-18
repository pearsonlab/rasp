import time
import numpy as np
import cv2
from nexus.store import Limbo, ObjectNotFoundError
from scipy.spatial.distance import cdist
from math import floor
import colorsys
from PyQt5 import QtGui, QtWidgets
import pyqtgraph as pg
from visual.front_end import FrontEnd
import sys
from nexus.actor import Actor, Spike
from queue import Empty
from collections import deque

import logging; logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(message)s',
                    handlers=[logging.FileHandler("example1.log"),
                              logging.StreamHandler()])

class DisplayVisual(Actor):
    ''' Class used to run a GUI + Visual as a single Actor 
    '''

    def run(self):
        logger.info('Loading FrontEnd')
        self.app = QtWidgets.QApplication([])
        # screen_resolution = self.app.desktop().screenGeometry()
        self.rasp = FrontEnd(self.visual, self.q_comm)
        self.rasp.show()
        logger.info('GUI ready')
        self.q_comm.put([Spike.ready()])
        self.visual.q_comm.put([Spike.ready()])
        self.app.exec_()
        logger.info('Done running GUI')

    def setup(self, visual=None):
        logger.info('Running setup for '+self.name)
        self.visual = visual
        self.visual.setup()

class CaimanVisual(Actor):
    ''' Class for displaying data from caiman processor
    '''

    def __init__(self, *args, showConnectivity=False):
        super().__init__(*args)

        self.com1 = np.zeros(2)
        self.selectedNeuron = 0
        self.selectedTune = None
        self.frame_num = 0
        self.showConnectivity = True #showConnectivity

        self.stimStatus = dict()
        for i in range(8):  # TODO: Hard-coded
            self.stimStatus[i] = deque()

        # self.flip = False #TODO

    def setup(self):
        ''' Setup 
        '''
        self.Cx = None
        self.C = None
        self.tune = None
        self.raw = None
        self.color = None
        self.coords = None
        self.w = None
        self.weight = None
        self.LL = None

        self.draw = True

        self.total_times = []
        self.timestamp = []

        self.window=500

    def run(self):
        pass #NOTE: Special case here, tied to GUI

    def getData(self):
        t = time.time()
        ids = None
        try:
            id = self.links['raw_frame_queue'].get(timeout=0.0001)
            self.raw_frame_number = list(id[0].keys())[0]
            self.raw = self.client.getID(id[0][self.raw_frame_number])
        except Empty as e:
            pass
        except Exception as e:
            logger.error('Visual: Exception in get data: {}'.format(e))
        try: 
            ids = self.q_in.get(timeout=0.0001)
            if ids is not None and ids[0]==1:
                print('visual: missing frame')
                self.frame_num += 1
                self.total_times.append([time.time(), time.time()-t])
                raise Empty
            self.frame_num = ids[-1]
            if self.draw:
                (self.Cx, self.C, self.Cpop, self.tune, self.color, self.coords, self.allStims, self.w, self.LL) = self.client.getList(ids[:-1])
                self.getCurves()
                self.getFrames()
                self.total_times.append([time.time(), time.time()-t])
            self.timestamp.append([time.time(), self.frame_num])
        except Empty as e:
            pass
        except ObjectNotFoundError as e:
            logger.error('Object not found, continuing...')
        except Exception as e:
            logger.error('Visual: Exception in get data: {}'.format(e))

        # self.total_times.append([time.time(), time.time()-t])

    def setStim(self, stim):
        # direction, onoff = stim[1], stim[0]
        # # print('dir: ', direction)
        # # print('onoff: ', onoff)
        # if onoff != 0 and -1 < direction < 8:
        #     self.stimStatus[direction].append(self.frame_num)
        #     print('frame: ', self.frame_num, ' direction: ', direction)
        pass

    def getCurves(self):
        ''' Return the fluorescence traces and calculated tuning curves
            for the selected neuron as well as the population average
            Cx is the time (overall or window) as x axis
            C is indexed for selected neuron and Cpop is the population avg
            tune is a similar list to C
        '''
        if self.tune is not None:
            self.selectedTune = self.tune[0][self.selectedNeuron]
            self.tuned = [self.selectedTune, self.tune[1]]
        else:
            self.tuned = None

        if self.frame_num > self.window:
            self.Cx = self.Cx[-self.window:]
            self.C = self.C[:, -len(self.Cx):]
            self.Cpop = self.Cpop[-len(self.Cx):]
            #self.LL = self.LL[-len(self.Cx):]
        
        return self.Cx, self.C[self.selectedNeuron,:], self.Cpop, self.tuned, self.LL#[:len(self.Cx)]

    def getFrames(self):
        ''' Return the raw and colored frames for display
        '''
        if self.raw is not None and self.raw.shape[0] > self.raw.shape[1]:
            self.raw = np.rot90(self.raw, 1)
        if self.color is not None and self.color.shape[0] > self.color.shape[1]:
            self.color = np.rot90(self.color, 1)

        if self.w is not None:
            self.sortInd = np.mean(np.abs(self.w),axis=0).argsort()
            # self.sortInd[:10].sort(axis=0)
            
            self.sortInd2 = np.mean(np.abs(self.w[self.sortInd]), axis=1).argsort()
            self.sortInd2[:10].sort(axis=0)
            # i1 = self.sortInd[:10]
            self.i2 = self.sortInd2[:10]
            self.weight = self.w[self.i2[:,None],self.i2]*10

            # strongest = np.mean(self.C,axis=1).argsort()
            # print('Strongest: ', strongest[:10])
            # weight = self.w[strongest[:10,None],strongest[:10]]*10

        return self.raw, self.color, self.weight

    def selectNeurons(self, x, y):
        ''' x and y are coordinates
            identifies which neuron is closest to this point
            and updates plotEstimates to use that neuron
        '''
        neurons = [o['neuron_id']-1 for o in self.coords]
        com = np.array([o['CoM'] for o in self.coords])
        #dist = cdist(com, [np.array([y, self.raw.shape[0]-x])])
        dist = cdist(com, [np.array([self.raw.shape[0]-x, self.raw.shape[1]-y])])
        if np.min(dist) < 50:
            selected = neurons[np.argmin(dist)]
            self.selectedNeuron = selected
            print('Red circle at ', com[selected])
            print('Tuning curve: ', self.tune[0][selected])
            #self.com1 = [np.array([self.raw.shape[0]-com[selected][1], com[selected][0]])]
            #self.com1 = [com[selected]]
            self.com1 = [np.array([self.raw.shape[0]-com[selected][0], self.raw.shape[1]-com[selected][1]])]
        else:
            logger.error('No neurons nearby where you clicked')
            #self.com1 = [np.array([self.raw.shape[0]-com[0][1], com[0][0]])]
            self.com1 = [com[0]]
        return self.com1

    def selectWeights(self, x, y):
        ''' x, y int
            lines 4 entry array: selected n_x, other_x, selected n_y, other_y
        '''
        # translate back to C order of neurons 
        nid = self.i2[x]
        # print('selected neuron ', nid)

        # highlight selected neuron
        com = np.array([o['CoM'] for o in self.coords])
        loc = [np.array([self.raw.shape[0]-com[nid][0], self.raw.shape[1]-com[nid][1]])]

        # draw lines between it and all other in self.weight
        lines = np.zeros((18,4))
        strengths = np.zeros(18)
        i=0
        for n in np.nditer(self.i2):
            # print('connected n', n)
            if n!=nid and i<9:
                if n<com.shape[0]:
                    ar = np.array([self.raw.shape[0]-com[nid][0], self.raw.shape[0]-com[n][0], self.raw.shape[1]-com[nid][1], self.raw.shape[1]-com[n][1]])
                    lines[i] = ar
                    strengths[i] = self.w[nid][n]
                else:
                    strengths[i] = 0
                i+=1

        sortInd3 = np.abs(self.w[:,nid]).argsort(axis=0)
        sortInd3[:10].sort(axis=0)
        i3 = sortInd3[:10]
        i=9
        for n in np.nditer(i3):
            if n!=nid and i<18:
                if n<com.shape[0]:
                    ar = np.array([self.raw.shape[0]-com[nid][0], self.raw.shape[0]-com[n][0], self.raw.shape[1]-com[nid][1], self.raw.shape[1]-com[n][1]])
                    lines[i] = ar
                    strengths[i] = self.w[n][nid]
                else:
                    strengths[i] = 0
                i+=1
                
        print('strengths ', strengths)

        #update self.color...or add as ROIs? currently ROIs

        return loc, lines, strengths

    def selectNW(self, x, y):
        ''' x, y int
            lines 4 entry array: selected n_x, other_x, selected n_y, other_y
        '''
        # translate back to C order of neurons 
        nid = self.selectedNeuron
        print('selected neuron ', nid)

        # highlight selected neuron
        com = np.array([o['CoM'] for o in self.coords])
        loc = [np.array([self.raw.shape[0]-com[nid][0], self.raw.shape[1]-com[nid][1]])]

        # draw lines between it and 10 strongest connections in self.w
        sortInd2 = np.mean(np.abs(self.w[nid]), axis=0).argsort()
        sortInd2[:10].sort(axis=0)
        i2 = sortInd2[:10]

        # sortInd3 = np.mean(np.abs(self.w[:,nid]), axis=0).argsort()
        # sortInd3[:10].sort(axis=0)
        # i3 = sortInd3[:10]

        # lines = np.zeros((18,4))
        # strengths = np.zeros(18)
        # i=0
        # for n in np.nditer(i2):
        #     # print('connected n', n)
        #     if n!=nid and i<9:
        #         if n<com.shape[0]:
        #             ar = np.array([self.raw.shape[0]-com[nid][0], self.raw.shape[0]-com[n][0], self.raw.shape[1]-com[nid][1], self.raw.shape[1]-com[n][1]])
        #             lines[i] = ar
        #             strengths[i] = self.w[nid][n]
        #         else:
        #             strengths[i] = 0
        #         i+=1
        # i=9
        # for n in np.nditer(i3):
        #     print('connected n', n)
        #     if n!=nid and i<18:
        #         if n<com.shape[0]:
        #             ar = np.array([self.raw.shape[0]-com[nid][0], self.raw.shape[0]-com[n][0], self.raw.shape[1]-com[nid][1], self.raw.shape[1]-com[n][1]])
        #             lines[i] = ar
        #             strengths[i] = self.w[n][nid]
        #         else:
        #             strengths[i] = 0
        #         i+=1

        lines = np.zeros((18,4))
        strengths = np.zeros(18)
        i=0
        for n in np.nditer(self.i2):
            # print('connected n', n)
            if n!=nid and i<9:
                if n<com.shape[0]:
                    ar = np.array([self.raw.shape[0]-com[nid][0], self.raw.shape[0]-com[n][0], self.raw.shape[1]-com[nid][1], self.raw.shape[1]-com[n][1]])
                    lines[i] = ar
                    strengths[i] = self.w[nid][n]
                else:
                    strengths[i] = 0
                i+=1

        sortInd3 = np.abs(self.w[:,nid]).argsort(axis=0)
        sortInd3[:10].sort(axis=0)
        i3 = sortInd3[:10]
        i=9
        for n in np.nditer(i3):
            if n!=nid and i<18:
                if n<com.shape[0]:
                    ar = np.array([self.raw.shape[0]-com[nid][0], self.raw.shape[0]-com[n][0], self.raw.shape[1]-com[nid][1], self.raw.shape[1]-com[n][1]])
                    lines[i] = ar
                    strengths[i] = self.w[n,nid]
                else:
                    strengths[i] = 0
                i+=1
                
        print('strengths ', strengths)

        #update self.color...or add as ROIs? currently ROIs

        return loc, lines, strengths

    def getFirstSelect(self):
        first = None
        if self.coords:
            com = [o['CoM'] for o in self.coords]
            #first = [np.array([self.raw.shape[0]-com[0][1], com[0][0]])]
            first = [np.array([self.raw.shape[0]-com[0][0], self.raw.shape[1]-com[0][1]])]
            #first = [com[0]]
        return first

    def plotThreshFrame(self, thresh_r):
        ''' Computes shaded frame for targeting panel
            based on threshold value of sliders (user-selected)
        '''
        if self.raw is not None:
            bnd_Y = np.percentile(self.raw, (0.001,100-0.001))
            image = (self.raw - bnd_Y[0])/np.diff(bnd_Y)
        else:
            return None
        if image.shape[0] > image.shape[1]:
                image = np.rot90(image,1)
        if image is not None:
            image2 = np.stack([image, image, image, image], axis=-1).astype(np.uint8).copy()
            image2[...,3] = 150
            if self.coords is not None:
                coords = [o['coordinates'] for o in self.coords]
                for i,c in enumerate(coords):
                    ind = c[~np.isnan(c).any(axis=1)].astype(int)
                    #rot_ind = np.array([[i[1],self.raw.shape[0]-i[0]] for i in ind])
                    #rot_ind = np.array([[self.raw.shape[0]-i[0],self.raw.shape[1]-i[1]] for i in ind])
                    cv2.fillConvexPoly(image2, ind, self._threshNeuron(i, thresh_r))
            return image2
        else: 
            return None

    def _threshNeuron(self, ind, thresh_r):
        if self.tune is not None:
            ests = self.tune[0]
            thresh = np.max(thresh_r)
            display = (255,255,255,150)
            act = np.zeros(ests.shape[1])
            if ests[ind] is not None:
                intensity = np.max(ests[ind])
                act[:len(ests[ind])] = ests[ind]
                if thresh > intensity: 
                    display = (255,255,255,0)
                elif np.any(act[np.where(thresh_r[:-1]==0)[0]]>0.5):
                    display = (255,255,255,0)
        else:
            display = (255,255,255,0)
        return display