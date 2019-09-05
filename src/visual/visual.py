import time
import numpy as np
import cv2
from typing import Sequence
from nexus.store import Limbo, ObjectNotFoundError
from scipy.spatial.distance import cdist
from math import floor
import colorsys
from PyQt5 import QtGui, QtWidgets
import pyqtgraph as pg
from visual.front_end import FrontEnd
import sys
from nexus.module import Module, Spike
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
        self.q_comm.put(Spike.ready())
        self.visual.q_comm.put([Spike.ready()])
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
        self.rotater: Rotater = None
        self.newFrameAvail = {'raw': False, 'color': False, 'image': False}
        self.showMask = True


    def setup(self):
        ''' Setup 
        '''
        self.Cx = None
        self.C = None
        self.tune = None
        self.raw = None
        self.color = None
        self.colorMask = None
        self.threshFrame = None
        self.coords = None

        self.draw = True

        self.total_times = []
        self.timestamp = []

    def getData(self):
        t = time.time()
        try:
            id = self.links['raw_frame_queue'].get(timeout=0.0001)
            self.raw_frame_number = list(id[0].keys())[0]
            self.raw = self.client.getID(id[0][self.raw_frame_number])
            self.newFrameAvail['raw'] = True
        except Empty as e:
            pass
        except Exception as e:
            logger.error('Visual: Exception in get data: {}'.format(e))
        try: 
            ids = self.q_in.get(timeout=0.0001)
            if self.draw:
                (self.Cx, self.C, self.Cpop, self.tune, self.color, self.colorMask, self.coords) = self.client.getList(ids)
                self.newFrameAvail['color'] = True
                self.newFrameAvail['image'] = True
                self.total_times.append([time.time(), time.time()-t])
            ##############FIXME frame number!
            self.frame_num += 1
            self.timestamp.append([time.time(), self.frame_num])
        except Empty as e:
            pass #logger.info('Visual: No data from queue') #no data
        except ObjectNotFoundError as e:
            logger.error('Object not found, continuing...')
        except Exception as e:
            logger.error('Visual: Exception in get data: {}'.format(e))

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
        if self.raw is not None and self.color is not None and self.rotater is None:  # First time
            self.rotater = Rotater(img_dim=self.raw.shape)

        if self.newFrameAvail['color'] and self.rotater is not None:
            self.color, self.colorMask = self.rotater.rotate_image(self.color, self.colorMask)
            self.newFrameAvail['color'] = False

        if self.newFrameAvail['raw'] and self.rotater is not None:
            self.raw = self.rotater.rotate_image(self.raw)
            self.newFrameAvail['raw'] = False

        if self.showMask:
            return self.raw, self.colorMask
        else:
            return self.raw, self.color

    def triggerMask(self):
        self.showMask = False if self.showMask else True

    def selectNeurons(self, x, y):
        ''' x and y are coordinates
            identifies which neuron is closest to this point
            and updates plotEstimates to use that neuron
        '''
        #TODO: flip x and y if self.flip = True 
        neurons = [o['neuron_id']-1 for o in self.coords]
        com = np.array([o['CoM'] for o in self.coords])
        #dist = cdist(com, [np.array([y, self.raw.shape[0]-x])])
        dist = cdist(self.rotater.rotate_coord(com, 'CoM'), [np.array([x, y])])
        if np.min(dist) < 50:
            selected = neurons[np.argmin(dist)]
            self.selectedNeuron = selected
            #self.com1 = [np.array([self.raw.shape[0]-com[selected][1], com[selected][0]])]
            self.com1 = [com[selected]]
        else:
            logger.error('No neurons nearby where you clicked')
            #self.com1 = [np.array([self.raw.shape[0]-com[0][1], com[0][0]])]
            self.com1 = [com[0]]
        return self.com1

    def getFirstSelect(self):
        first = None
        if self.coords:
            com = [o['CoM'] for o in self.coords] #TODO make one line
            #first = [np.array([self.raw.shape[0]-com[0][1], com[0][0]])]
            first = [com[0]]
        return first

    def plotThreshFrame(self, thresh_r):
        ''' Computes shaded frame for targeting panel
            based on threshold value of sliders (user-selected)
        '''
        if self.raw is not None and self.newFrameAvail['image']:
            bnd_Y = np.percentile(self.raw, (0.001,100-0.001))
            image = (self.raw - bnd_Y[0])/np.diff(bnd_Y)
            if image.shape[0] > image.shape[1]:
                image = np.rot90(image,1)
            image2 = np.stack([image, image, image, image], axis=-1).astype(np.uint8).copy()
            image2[...,3] = 150
            if self.coords is not None:
                coords = [o['coordinates'] for o in self.coords]
                for i,c in enumerate(coords):
                    #c = np.array(c)
                    ind = c[~np.isnan(c).any(axis=1)].astype(int)
                    ind = self.rotater.rotate_coord(ind, 'contour')
                    #rot_ind = np.array([[i[1],self.raw.shape[0]-i[0]] for i in ind])
                    cv2.fillConvexPoly(image2, ind, self._threshNeuron(i, thresh_r))
            self.threshFrame = image2
            self.newFrameAvail['image'] = False

        return self.threshFrame

    def _threshNeuron(self, ind, thresh_r):
        ests = self.tune[0]

        dark = (255,255,255,0)
        bright = (255,255,255,150)

        thresh = np.max(thresh_r)
        display = bright
        act = np.zeros(ests.shape[1])
        if ests[ind] is not None:
            intensity = np.max(ests[ind])
            act[:len(ests[ind])] = ests[ind]
            if intensity < thresh:
                display = dark
            elif np.any(act[np.where(thresh_r==0)[0]] > 0.5):
                display = dark
        return display


class Rotater:
    """
    Class for rotation of images and all components within to ensure that all images are vertical for display.
    """
    def __init__(self, img_dim: tuple):
        assert len(img_dim) == 2 and min(img_dim) > 0
        self.img_dim = img_dim
        self.rotate = True if img_dim[0] > img_dim[1] else False
        self.idx = {'contour': 1,
                    'CoM': 0}

    def _rotate(self, img: np.ndarray):
        assert img.shape[:2] == self.img_dim
        return np.rot90(img) if self.rotate else img

    def rotate_image(self, *imgs: np.ndarray):
        if len(imgs) == 1:
            return self._rotate(imgs[0])

        if isinstance(imgs[0], Sequence):
            return (self._rotate(img) for img in imgs[0])

        return (self._rotate(img) for img in imgs)

    def rotate_coord(self, coord: np.ndarray, type_):
        assert type_ in self.idx.keys()
        if self.rotate:
            coord[:, [1, 0]] = coord[:, [0, 1]]
            coord[:, self.idx[type_]] = self.img_dim[1] - coord[:, self.idx[type_]]
        return coord

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