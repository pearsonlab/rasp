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
from nexus.module import Module
from queue import Empty

import logging; logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(message)s',
                    handlers=[logging.FileHandler("example1.log"),
                              logging.StreamHandler()])

class DisplayVisual(Module):

    def run(self):
        logger.info('Loading FrontEnd')
        self.app = QtWidgets.QApplication([])
#        screen_resolution = self.app.desktop().screenGeometry()
        self.rasp = FrontEnd(self.visual, self.q_comm)
        self.rasp.show()
        logger.info('GUI ready')
        self.app.exec_()
        logger.info('Done running GUI')

    def setup(self, visual=None):
        logger.info('Running setup for '+self.name)
        self.visual = visual
        self.visual.setup()


class Visual(Module):
    '''Abstract lass for displaying data
    '''
    def plotEstimates(self):
        ''' Always need to plot some kind of estimates
        '''
        raise NotImplementedError

    def run(self):
        ''' Currently not running independently
        TODO: FIXME: implement this? Or leave tied to GUI?
        '''
        pass

class CaimanVisual(Visual):
    ''' Class for displaying data from caiman processor
    '''

    def __init__(self, *args):
        super().__init__(*args)

        # self.plots = [0,1,2]
        self.com1 = np.zeros(2)
        self.neurons = []
        self.estsAvg = []
        self.frame = 0
        self.selectedNeuron = 0
        self.selectedTune = None
        self.frame_num = 0

        self.flip = False
        self.flag = False

    def setup(self):
        ''' Setup 
        '''
        self.Cx = None
        self.C = None
        self.tune = None
        self.raw = None
        self.color = None
        self.coords = None

        self.total_times = []

    def getData(self):
        t = time.time()
        try: 
            ids = self.q_in.get(timeout=0.005)
            res = []
            for id in ids:
                res.append(self.client.getID(id))
            # expect Cx, C, tune, raw, color, coords from Analysis module
            (self.Cx, self.C, self.Cpop, self.tune, self.raw, self.color, self.coords) = res
            ##############FIXME frame number!
            self.frame_num += 1
        except Empty as e:
            pass #logger.info('Visual: No data from queue') #no data
        except ObjectNotFoundError as e:
            logger.error('Object not found, continuing...')
        except Exception as e:
            logger.error('Visual: Exception in get data: {}'.format(e))

        self.total_times.append(time.time()-t)  

    def getCurves(self):
        ''' Return the fluorescence traces and calculated tuning curves
            for the selected neuron as well as the population average
            Cx is the time (overall or window) as x axis
            C is indexed for selected neuron and Cpop is the population avg
            tune is a similar list to C
        '''
        if self.tune is not None:
            self.selectedTune = self.tune[0][self.selectedNeuron,:]

        return self.Cx, self.C[self.selectedNeuron,:], self.Cpop, [self.selectedTune, self.tune[1]]

    def getFrames(self):
        ''' Return the raw and colored frames for display
        '''
        return self.raw, self.color

    def selectNeurons(self, x, y):
        ''' x and y are coordinates
            identifies which neuron is closest to this point
            and updates plotEstimates to use that neuron
        '''
        #TODO: flip x and y if self.flip = True 

        neurons = [o['neuron_id']-1 for o in self.coords]
        com = np.array([o['CoM'] for o in self.coords])
        dist = cdist(com, [np.array([y, x])])
        if np.min(dist) < 50:
            selected = neurons[np.argmin(dist)]
            self.selectedNeuron = selected
            self.com1 = com[selected]
        else:
            logger.error('No neurons nearby where you clicked')
            self.com1 = com[0]
        return self.com1

    def getFirstSelect(self):
        first = None
        if self.neurons:
            first = [np.array(self.neurons[0])]
        return first

    def plotThreshFrame(self, thresh_r):
        ''' Computes shaded frame for targeting panel
            based on threshold value of sliders (user-selected)
        '''
        image = self.raw
        image2 = np.stack([image, image, image, image], axis=-1).astype(np.uint8).copy()
        image2[...,3] = 100
        if self.coords is not None:
            coords = [o['coordinates'] for o in self.coords]
            for i,c in enumerate(coords):
                c = np.array(c)
                ind = c[~np.isnan(c).any(axis=1)].astype(int)
                cv2.fillConvexPoly(image2, ind, self._threshNeuron(i, thresh_r))

        if self.color.shape[0] < self.color.shape[1]:
            self.flip = True
        else:
            np.swapaxes(image2,0,1)
        #TODO: add rotation to user preferences and/or user clickable input
        return np.rot90(image2,1)

    def _threshNeuron(self, ind, thresh_r):
        ests = self.tune[0]
        thresh = np.max(thresh_r)
        display = (255,255,255,150)
        act = np.zeros(11)
        if ests[ind] is not None:
            intensity = np.max(ests[ind])
            act[:len(ests[ind])] = ests[ind]
            if thresh > intensity: 
                display = (255,255,255,0)
            elif np.any(act[np.where(thresh_r==0)[0]]>0.5):
                display = (255,255,255,0)
        return display

#------------  Code below for running idependently 

def runVis():
    logger.error('trying to run')
    app = QtWidgets.QApplication([]) #.instance() #(sys.argv)
    print('type ', type(app))
    logger.error('trying to run after app')
    rasp = FrontEnd()
    rasp.show()
    app.exec_()

if __name__=="__main__":
    vis = CaimanVisual('name', 'client')
    from multiprocessing import Process
    p = Process(target=runVis)
    p.start()
    input("Type any key to quit.")
    print("Waiting for graph window process to join...")
    p.join()
    print("Process joined successfully. C YA !")