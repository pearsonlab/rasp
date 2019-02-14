import time
import numpy as np
import cv2
from nexus.store import Limbo
from scipy.spatial.distance import cdist
from skimage.measure import find_contours
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
        

    def plotContours(self, A, dims):
        ''' Provide contours to plot atop raw image
        '''
        coords = self.get_contours(A, dims)
        return [o['coordinates'] for o in coords]

    def plotCoM(self, A, dims):
        ''' Provide contours to plot atop raw image
        '''
        newNeur = None
        coords = self.get_contours(A, dims) #TODO: just call self.com directly? order matters!
        if len(self.neurons) < len(coords):
            #print('adding ', len(coords)-len(self.neurons), ' neurons')
            newNeur = [o['CoM'] for o in coords[len(self.neurons):]]
            self.neurons.extend(newNeur)
        return newNeur

    def get_contours(self, A, dims, thr=0.9, thr_method='nrg', swap_dim=False):
        ''' Stripped-down version of visualization get_contours function from caiman'''

        """Gets contour of spatial components and returns their coordinates

        Args:
            A:   np.ndarray or sparse matrix
                    Matrix of Spatial components (d x K)

                dims: tuple of ints
                    Spatial dimensions of movie (x, y[, z])

                thr: scalar between 0 and 1
                    Energy threshold for computing contours (default 0.9)

                thr_method: [optional] string
                    Method of thresholding:
                        'max' sets to zero pixels that have value less than a fraction of the max value
                        'nrg' keeps the pixels that contribute up to a specified fraction of the energy

        Returns:
            Coor: list of coordinates with center of mass and
                    contour plot coordinates (per layer) for each component
        """

        # if 'csc_matrix' not in str(type(A)):
        #     A = csc_matrix(A)
        d, nr = np.shape(A)
        
        d1, d2 = dims
        x, y = np.mgrid[0:d1:1, 0:d2:1]

        coordinates = []

        # get the center of mass of neurons( patches )
        cm = self.com(A, *dims)

        # for each patches
        #TODO: this does NOT need to be recomputed except when update_shapes has changes...
        for i in range(nr):
            pars = dict()
            # we compute the cumulative sum of the energy of the Ath component that has been ordered from least to highest
            patch_data = A.data[A.indptr[i]:A.indptr[i + 1]]
            indx = np.argsort(patch_data)[::-1]
            if thr_method == 'nrg':
                cumEn = np.cumsum(patch_data[indx]**2)
                # we work with normalized values
                cumEn /= cumEn[-1]
                Bvec = np.ones(d)
                # we put it in a similar matrix
                Bvec[A.indices[A.indptr[i]:A.indptr[i + 1]][indx]] = cumEn
            else:
                if thr_method != 'max':
                    logger.warning("Unknown threshold method. Choosing max")
                Bvec = np.zeros(d)
                Bvec[A.indices[A.indptr[i]:A.indptr[i + 1]]] = patch_data / patch_data.max()

            if swap_dim:
                Bmat = np.reshape(Bvec, dims, order='C')
            else:
                Bmat = np.reshape(Bvec, dims, order='F')
            pars['coordinates'] = []
            # for each dimensions we draw the contour
            for B in (Bmat if len(dims) == 3 else [Bmat]):
                vertices = find_contours(B.T, thr)
                # this fix is necessary for having disjoint figures and borders plotted correctly
                v = np.atleast_2d([np.nan, np.nan])
                for _, vtx in enumerate(vertices):
                    num_close_coords = np.sum(np.isclose(vtx[0, :], vtx[-1, :]))
                    if num_close_coords < 2:
                        if num_close_coords == 0:
                            # case angle
                            newpt = np.round(vtx[-1, :] / [d2, d1]) * [d2, d1]
                            vtx = np.concatenate((vtx, newpt[np.newaxis, :]), axis=0)
                        else:
                            # case one is border
                            vtx = np.concatenate((vtx, vtx[0, np.newaxis]), axis=0)
                    v = np.concatenate(
                        (v, vtx, np.atleast_2d([np.nan, np.nan])), axis=0)

                pars['coordinates'] = v if len(
                    dims) == 2 else (pars['coordinates'] + [v])
            pars['CoM'] = np.squeeze(cm[i, :])
            pars['neuron_id'] = i + 1
            coordinates.append(pars)
        return coordinates

    def com(self, A, d1, d2):
        
        Coor = np.matrix([np.outer(np.ones(d2), np.arange(d1)).ravel(),
                            np.outer(np.arange(d2), np.ones(d1)).ravel()], dtype=A.dtype)
        cm = (Coor * A / A.sum(axis=0)).T
        return np.array(cm)