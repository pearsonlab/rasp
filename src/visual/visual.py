import time
import numpy as np
import cv2
from nexus.store import Limbo
from scipy.spatial.distance import cdist
from skimage.measure import find_contours
from math import floor
import colorsys
from PyQt5 import QtGui, QtWidgets
import pyqtgraph as pg
from visual.front_end import FrontEnd
import sys
from scipy.sparse import csc_matrix
from nexus.module import Module

import logging; logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DisplayVisual():
    def __init__(self, name):
        self.name = name

    def runGUI(self):
        logger.info('Loading FrontEnd')
        self.app = QtWidgets.QApplication([])
#        screen_resolution = self.app.desktop().screenGeometry()
        self.rasp = FrontEnd(self.visual, self.link)
        self.rasp.show()
        logger.info('GUI ready')
        self.app.exec_()
        logger.info('Done running GUI')

    def setVisual(self, Visual):
        self.visual = Visual

    def setLink(self, link):
        print('setting link ', link)
        self.link = link

class Visual(Module):
    '''Abstract lass for displaying data
    '''
    def plotEstimates(self):
        ''' Always need to plot some kind of estimates
        '''
        raise NotImplementedError

    def run(self):
        ''' Currently not running independently
        TODO: FIXME: implement this
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
        self.coords = None
        self.frame = 0
        self.image = None
        self.raw = None
        self.A = None
        self.dims = None
        self.flip = False

    def setup(self):
        ''' Setup 
        '''
        pass

    # def plotEstimates(self):
    #     ''' Take numpy estimates and t=frame_number
    #         Create X and Y for plotting, return
    #     '''
    #     try:
    #         #(ests, A, dims, self.image, self.raw) = self.q_in.get(timeout=1)
    #         ids = self.q_in.get(timeout=1)
    #         res = []
    #         for id in ids:
    #             res.append(self.client.getID(id))
    #         (ests, A, dims, self.image, self.raw) = res
            
    #         self.coords = self._updateCoords(A, dims)
    #         #self.coords = self.get_contours(self.A, self.dims)
            
    #         self.frame += 1

    #         stim = self.stimAvg(ests)
    #         avg = stim[0]
    #         avgAvg = np.array(np.mean(stim, axis=0))

    #         if self.frame >= 200:
    #             # TODO: change to init batch here
    #             window = 200
    #         else:
    #             window = self.frame

    #         if ests.shape[1]>0:
    #             Yavg = np.mean(ests[:,self.frame-window:self.frame], axis=0) 
    #             #Y0 = ests[self.plots[0],frame_number-window:frame_number]
    #             Y1 = ests[0,self.frame-window:self.frame]
    #             X = np.arange(0,Y1.size)+(self.frame-window)
    #             return X,[Y1,Yavg],avg,avgAvg
        
    #     except Exception as e:
    #         print('probably timeout ', e)
    #         return None

    def selectNeurons(self, x, y):
        ''' x and y are coordinates
            identifies which neuron is closest to this point
            and updates plotEstimates to use that neuron
        '''
        #TODO: flip x and y if self.flip = True 

        coords = self.coords
        neurons = [o['neuron_id']-1 for o in coords]
        com = np.array([o['CoM'] for o in coords])
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
        image = self.image
        image2 = np.stack([image, image, image, image], axis=-1).astype(np.uint8).copy()
        image2[...,3] = 100
        if self.coords is not None:
            coords = [o['coordinates'] for o in self.coords]
            for i,c in enumerate(coords):
                c = np.array(c)
                ind = c[~np.isnan(c).any(axis=1)].astype(int)
                cv2.fillConvexPoly(image2, ind, self._threshNeuron(i, thresh_r))

        if self.image.shape[0] < self.image.shape[1]:
                self.flip = True
        else:
            np.swapaxes(image2,0,1)
        #TODO: add rotation to user preferences and/or user clickable input

        return image2

    def _threshNeuron(self, ind, thresh_r):
        thresh = np.max(thresh_r)
        display = (255,255,255,150)
        act = np.zeros(11)
        if self.estsAvg[ind] is not None:
            intensity = np.max(self.estsAvg[ind])
            act[:len(self.estsAvg[ind])] = self.estsAvg[ind]
            if thresh > intensity: 
                display = (255,255,255,0)
            elif np.any(act[np.where(thresh_r==0)[0]]>0.5):
                display = (255,255,255,0)
        return display

    # def _tuningColor(self, ind, inten):
    #     if self.estsAvg[ind] is not None:
    #         ests = np.array(self.estsAvg[ind])
    #         h = np.argmax(ests)*36/360
    #         intensity = 1- np.mean(inten[0][0])/255.0
    #         r, g, b, = colorsys.hls_to_rgb(h, intensity, 0.8)
    #         r, g, b = [x*255.0 for x in (r, g, b)]
    #         return (r, g, b)+ (intensity*150,)
    #     else:
    #         return (255,255,255,0)

    # def _updateCoords(self, A, dims):
    #     '''See if we need to recalculate the coords
    #        Also see if we need to add components
    #     '''
    #     if self.A is None: #initial calculation
    #         self.A = A
    #         self.dims = dims
    #         self.coords = self.get_contours(self.A, self.dims)

    #     elif np.shape(A)[1] > np.shape(self.A)[1]: #Only recalc if we have new components
    #         self.A = A
    #         self.dims = dims
    #         self.coords = self.get_contours(self.A, self.dims)

    #     return self.coords  #Not really necessary
        
    # def plotContours(self, A, dims):
    #     ''' Provide contours to plot atop raw image
    #     '''
    #     coords = self.get_contours(A, dims)
    #     return [o['coordinates'] for o in coords]

    # def plotCoM(self, A, dims):
    #     ''' Provide contours to plot atop raw image
    #     '''
    #     newNeur = None
    #     coords = self.get_contours(A, dims) #TODO: just call self.com directly? order matters!
    #     if len(self.neurons) < len(coords):
    #         #print('adding ', len(coords)-len(self.neurons), ' neurons')
    #         newNeur = [o['CoM'] for o in coords[len(self.neurons):]]
    #         self.neurons.extend(newNeur)
    #     return newNeur

    # def get_contours(self, A, dims, thr=0.9, thr_method='nrg', swap_dim=False):
    #     ''' Stripped-down version of visualization get_contours function from caiman'''

    #     """Gets contour of spatial components and returns their coordinates

    #     Args:
    #         A:   np.ndarray or sparse matrix
    #                 Matrix of Spatial components (d x K)

    #             dims: tuple of ints
    #                 Spatial dimensions of movie (x, y[, z])

    #             thr: scalar between 0 and 1
    #                 Energy threshold for computing contours (default 0.9)

    #             thr_method: [optional] string
    #                 Method of thresholding:
    #                     'max' sets to zero pixels that have value less than a fraction of the max value
    #                     'nrg' keeps the pixels that contribute up to a specified fraction of the energy

    #     Returns:
    #         Coor: list of coordinates with center of mass and
    #                 contour plot coordinates (per layer) for each component
    #     """

    #     if 'csc_matrix' not in str(type(A)):
    #         A = csc_matrix(A)
    #     d, nr = np.shape(A)
        
    #     d1, d2 = dims
    #     x, y = np.mgrid[0:d1:1, 0:d2:1]

    #     coordinates = []

    #     # get the center of mass of neurons( patches )
    #     cm = self.com(A, *dims)

    #     # for each patches
    #     #TODO: this does NOT need to be recomputed except when update_shapes has changes...
    #     for i in range(nr):
    #         pars = dict()
    #         # we compute the cumulative sum of the energy of the Ath component that has been ordered from least to highest
    #         patch_data = A.data[A.indptr[i]:A.indptr[i + 1]]
    #         indx = np.argsort(patch_data)[::-1]
    #         cumEn = np.cumsum(patch_data[indx]**2)
    #         # we work with normalized values
    #         cumEn /= cumEn[-1]
    #         Bvec = np.ones(d)
    #         # we put it in a similar matrix
    #         Bvec[A.indices[A.indptr[i]:A.indptr[i + 1]][indx]] = cumEn
    #         Bmat = np.reshape(Bvec, dims, order='F')
    #         pars['coordinates'] = []
    #         # for each dimensions we draw the contour
    #         for B in (Bmat if len(dims) == 3 else [Bmat]):
    #             vertices = find_contours(B.T, thr)
    #             # this fix is necessary for having disjoint figures and borders plotted correctly
    #             v = np.atleast_2d([np.nan, np.nan])
    #             for _, vtx in enumerate(vertices):
    #                 num_close_coords = np.sum(np.isclose(vtx[0, :], vtx[-1, :]))
    #                 if num_close_coords < 2:
    #                     if num_close_coords == 0:
    #                         # case angle
    #                         newpt = np.round(vtx[-1, :] / [d2, d1]) * [d2, d1]
    #                         vtx = np.concatenate((vtx, newpt[np.newaxis, :]), axis=0)
    #                     else:
    #                         # case one is border
    #                         vtx = np.concatenate((vtx, vtx[0, np.newaxis]), axis=0)
    #                 v = np.concatenate(
    #                     (v, vtx, np.atleast_2d([np.nan, np.nan])), axis=0)

    #             pars['coordinates'] = v if len(
    #                 dims) == 2 else (pars['coordinates'] + [v])
    #         pars['CoM'] = np.squeeze(cm[i, :])
    #         pars['neuron_id'] = i + 1
    #         coordinates.append(pars)
    #     return coordinates

    # def com(self, A, d1, d2):
        
    #     Coor = np.matrix([np.outer(np.ones(d2), np.arange(d1)).ravel(),
    #                         np.outer(np.arange(d2), np.ones(d1)).ravel()], dtype=A.dtype)
    #     cm = (Coor * A / A.sum(axis=0)).T
    #     return np.array(cm)

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