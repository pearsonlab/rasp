from nexus.module import Module, Spike
import logging; logger = logging.getLogger(__name__)


class Analysis(Module):
    '''Abstract class for the analysis module
    Performs additional computations on the extracted
    neural activity from the processor module
    '''
    #def putAnalysis(self):
    #    # Update the DS with analysis
    #    raise NotImplementedError


class MeanAnalysis(Analysis):
    def __init__(self, *args):
        super().__init__(*args)

    def setup(self, param_file=None):
        '''
        '''
        # TODO: same as behaviorAcquisition, need number of stimuli here. TODO: make adaptive later
        self.num_stim = 10 
        self.frame = 0
        self.ests = None
        self.flag = False
        self.curr_stim = 0 #start with zeroth stim unless signaled otherwise
        self.stimInd = []

    def run(self, ests):
        # ests structure: np.array([components, frames])
        while True:
            if self.flag:
                try:
                    self.runAvg()
                    if self.done:
                        logger.info('Analysis is done, exiting')
                        return
                except Exception as e:
                    logger.error('Analysis exception during run: {}'.format(e))
                    break 
            try: 
                signal = self.q_sig.get(timeout=1)
                if signal == Spike.run(): 
                    self.flag = True
                    logger.warning('Received run signal, begin running')
                elif signal == Spike.quit():
                    logger.warning('Received quit signal, aborting')
                    break    
                elif signal == Spike.pause():
                    logger.warning('Received pause signal, pending...')
                    self.flag = False
                elif signal == Spike.resume(): #currently treat as same as run
                    logger.warning('Received resume signal, resuming')
                    self.flag = True 
            except Empty as e:
                pass #no signal from Nexus
            try: 
                sig = self.input_stim_queue(timeout=1)
                self.updateStim(sig)
            except Empty as e:
                pass #no change in input stimulus
                #TODO: other errors

    def runAvg(self):
        ''' Take numpy estimates and frame_number
            Create X and Y for plotting
        '''
        self.frame += 1
        self.stimInd.append(self.curr_stim)
        try:
            ids = self.q_in.get(timeout=1)
            res = []
            for id in ids:
                res.append(self.client.getID(id))
            (ests, A, self.image, self.raw) = res
            #TODO: add error handling for if we received some but not all of these
            
            dims = self.image.shape
            self.coords = self._updateCoords(A, dims)

            self.raw, self.color = self.plotColorFrame()
            
            self.stimAvg(ests)
            self.globalAvg = np.array(np.mean(self.stimAvg, axis=0))

            if self.frame >= 200:
                # TODO: change to init batch here
                window = 200
            else:
                window = self.frame

            if ests.shape[1]>0:
                self.Yavg = np.mean(ests[:,self.frame-window:self.frame], axis=0) 
                #self.Y1 = ests[0,self.frame-window:self.frame]
                self.X = np.arange(0,Yavg.size)+(self.frame-window)
                #return X,[Y1,Yavg],avg,allAvg
            
            self.putAnalysis()
        
        except Exception as e:
            print('probably timeout ', e)

    def updateStim(self, stim):
        ''' Recevied new signal from Behavior Acquirer to change input stimulus
        '''
        self.curr_stim = stim
        # possibly other action items here...? Validation?

    def putAnalysis(self):
        ''' Throw things to DS and put IDs in queue for Visual
        '''
        ids = []
        ids.append(self.client.put(self.estsAvg, 'estsAvg'+str(self.frame)))
        ids.append(self.client.put(self.X, 'X'+str(self.frame)))
        ids.append(self.client.put(self.Yavg, 'Yavg'+str(self.frame)))
        ids.append(self.client.put(self.globalAvg, 'globalAvg'+str(self.frame)))
        ids.append(self.client.put(self.raw, 'raw'+str(self.frame)))
        ids.append(self.client.put(self.color, 'color'+str(self.frame)))

        self.q_out.put(ids)

    def stimAvg(self, ests):
        ''' Using stimInd as mask, average ests across each input stimulus
        '''
        estsAvg = []
        for i in range(ests.shape[0]): #for each component
            tmpList = []
            for j in range(int(np.floor(ests.shape[1]/100))+1): #average over stim window
                tmp = np.mean(ests[int(i)][int(j)*100:int(j)*100+100])
                tmpList.append(tmp)
            estsAvg.append(tmpList)
        self.estsAvg = np.array(estsAvg)        
        return self.estsAvg

    def plotColorFrame(self):
        ''' Computes colored nicer background+components frame
        '''
        image = self.image
        raw = self.raw
        color = np.stack([image, image, image, image], axis=-1).astype(np.uint8).copy()
        color[...,3] = 255
        if self.coords is not None:
            coords = [o['coordinates'] for o in self.coords]
            for i,c in enumerate(coords):
                c = np.array(c)
                ind = c[~np.isnan(c).any(axis=1)].astype(int)
                cv2.fillConvexPoly(color, ind, self._tuningColor(i, color[ind[:,1], ind[:,0]]))

        if self.image.shape[0] < self.image.shape[1]:
                self.flip = True
                raw = raw.T
        else:
            np.swapaxes(color,0,1)
            np.swapaxes(image2,0,1)
        #TODO: user input for rotating frame? See Visual class

        return np.flipud(raw), np.rot90(color,2)

    def _tuningColor(self, ind, inten):
        if self.estsAvg[ind] is not None:
            ests = np.array(self.estsAvg[ind])
            h = np.argmax(ests)*36/360
            intensity = 1- np.mean(inten[0][0])/255.0
            r, g, b, = colorsys.hls_to_rgb(h, intensity, 0.8)
            r, g, b = [x*255.0 for x in (r, g, b)]
            return (r, g, b)+ (intensity*150,)
        else:
            return (255,255,255,0)

    def _updateCoords(self, A, dims):
        '''See if we need to recalculate the coords
           Also see if we need to add components
        '''
        if self.A is None: #initial calculation
            self.A = A
            self.dims = dims
            self.coords = self.get_contours(self.A, self.dims)

        elif np.shape(A)[1] > np.shape(self.A)[1]: #Only recalc if we have new components
            self.A = A
            self.dims = dims
            self.coords = self.get_contours(self.A, self.dims)
        #return self.coords  #Not really necessary
    

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

        if 'csc_matrix' not in str(type(A)):
            A = csc_matrix(A)
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
            cumEn = np.cumsum(patch_data[indx]**2)
            # we work with normalized values
            cumEn /= cumEn[-1]
            Bvec = np.ones(d)
            # we put it in a similar matrix
            Bvec[A.indices[A.indptr[i]:A.indptr[i + 1]][indx]] = cumEn
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