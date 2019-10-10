import time
import pickle
import cv2
import numpy as np
import scipy.sparse
from nexus.store import Limbo, CannotGetObjectError, ObjectNotFoundError
from caiman.source_extraction import cnmf
from caiman.source_extraction.cnmf.utilities import detrend_df_f
from caiman.source_extraction.cnmf.online_cnmf import OnACID
from caiman.source_extraction.cnmf.params import CNMFParams
from caiman.motion_correction import motion_correct_iteration_fast, tile_and_correct
from caiman.utils.visualization import get_contours
import caiman as cm
from os.path import expanduser
import os
from queue import Empty
from nexus.actor import Actor, Spike, RunManager
import traceback

import logging; logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class CaimanProcessor(Actor):
    '''Wraps CaImAn/OnACID functionality to
       interface with our pipeline.
       Uses code from caiman/source_extraction/cnmf/online_cnmf.py
    '''
    def __init__(self, *args, config_file=None):
        super().__init__(*args)
        self.param_file = config_file

    def setup(self):
        ''' Create OnACID object and initialize it
                (runs initialize online)
        '''
        logger.info('Running setup for '+self.name)
        self.done = False
        self.dropped_frames = []
        self.coords = None
        self.ests = None
        self.A = None

        self.loadParams(param_file=self.param_file)
        self.params = self.client.get('params_dict')
        
        # MUST include inital set of frames
        # TODO: Institute check here as requirement to Nexus
        
        self.opts = CNMFParams(params_dict=self.params)
        self.onAc = OnACID(params = self.opts)
        self.frame_number = 0 #self.params['init_batch']
        #TODO: Need to rewrite init online as well to receive individual frames.
        self.onAc.initialize_online()
        self.max_shifts_online = self.onAc.params.get('online', 'max_shifts_online')

    def run(self):
        '''Run the processor continually on input frames
        '''
        self.fitframe_time = []
        self.putAnalysis_time = []
        self.procFrame_time = [] #aka t_motion
        self.detect_time = []
        self.shape_time = []
        self.flag = False
        self.total_times = []
        self.timestamp = []
        self.counter = 0

        with RunManager(self.name, self.runProcess, self.setup, self.q_sig, self.q_comm) as rm:
            logger.info(rm)
            
        print('Processor broke, avg time per frame: ', np.mean(self.total_times, axis=0))
        print('Processor got through ', self.frame_number, ' frames')
        np.savetxt('timing/process_frame_time.txt', np.array(self.total_times))
        np.savetxt('timing/process_timestamp.txt', np.array(self.timestamp))

        self.shape_time = np.array(self.onAc.t_shapes)
        self.detect_time = np.array(self.onAc.t_detect)

        np.savetxt('timing/fitframe_time.txt', np.array(self.fitframe_time))
        np.savetxt('timing/shape_time.txt', self.shape_time)
        np.savetxt('timing/detect_time.txt', self.detect_time)

        np.savetxt('timing/putAnalysis_time.txt', np.array(self.putAnalysis_time))
        np.savetxt('timing/procFrame_time.txt', np.array(self.procFrame_time))

        print('Number of times coords updated ', self.counter)

        if self.onAc.estimates.OASISinstances is not None:
            try:
                S = np.stack([osi.s for osi in self.onAc.estimates.OASISinstances])
                np.savetxt('end_spikes.txt', S)
            except Exception as e:
                logger.error('Exception {}: {} during frame number {}'.format(type(e).__name__, e, self.frame_number))
                print(traceback.format_exc())
        else:
            print('No OASIS')
        self.coords1 = [o['CoM'] for o in self.coords]
        print(self.coords1[0])
        print('type ', type(self.coords1[0]))
        np.savetxt('contours.txt', np.array(self.coords1))

    def runProcess(self):
        ''' Run process. Runs once per frame.
            Output is a location in the DS to continually
            place the Estimates results, with ref number that
            corresponds to the frame number (TODO)
        '''
        #TODO: Error handling for if these parameters don't work
            #should implement in Tweak (?) or getting too complicated for users..
        
        #proc_params = self.client.get('params_dict')
        output = self.params['output']
        init = self.params['init_batch']
        frame = self._checkFrames()
        
        if frame is not None:
            t = time.time()
            self.done = False
            try:
                self.frame = self.client.getID(frame[0][str(self.frame_number)])
                self.frame = self._processFrame(self.frame, self.frame_number+init)
                t2 = time.time()
                self._fitFrame(self.frame_number+init, self.frame.reshape(-1, order='F'))
                self.fitframe_time.append([time.time()-t2])
                self.putEstimates(self.onAc.estimates, output)
                self.timestamp.append([time.time(), self.frame_number])
            except ObjectNotFoundError:
                logger.error('Processor: Frame {} unavailable from store, droppping'.format(self.frame_number))
                self.dropped_frames.append(self.frame_number)
                self.q_out.put([1])
            except KeyError as e:
                logger.error('Processor: Key error... {0}'.format(e))
                # Proceed at all costs
                self.dropped_frames.append(self.frame_number)
            except Exception as e:
                logger.error('Processor error: {}: {} during frame number {}'.format(type(e).__name__, 
                                                                                            e, self.frame_number))
                print(traceback.format_exc())
                self.dropped_frames.append(self.frame_number)
            self.frame_number += 1
            self.total_times.append(time.time()-t)
        else:
            pass
            
    def loadParams(self, param_file=None):
        ''' Load parameters from file or 'defaults' into store
            TODO: accept user input from GUI
            This also effectively registers specific params
            that CaimanProcessor needs with Nexus
        '''

        if param_file is not None:
            try:
                params_dict = self._load_params_from_file(param_file)
            except Exception as e:
                logger.exception('File cannot be loaded. {0}'.format(e))
        else:
            # defaults from demo scripts; CNMFParams does not set
            # each parameter needed by default (TODO change that?)
            # TODO add parameter validation inside Tweak
            home = expanduser("~")
            cwd = os.getcwd()
            params_dict = {'fnames': [cwd+'/data/sample.h5'],
                   'fr': 3.6,
                   'decay_time': 0.5,
                   'gSig': (3,3),
                   'p': 1,
                   'min_SNR': 0.5,
                   'rval_thr': 0.8,
                   'ds_factor': 1,
                   'nb': 2,
                   'motion_correct': True,
                   'init_batch': 5,
                   'init_method': 'bare',
                   'normalize': True,
                   'sniper_mode': True,
                   'K': 10,
                   'epochs': 1,
                   'max_shifts_online': np.ceil(10).astype('int'),
                   'pw_rigid': False,
                   'dist_shape_update': True,
                   'show_movie': False,
                #    'update_freq': 50,
                   'minibatch_shape': 5,
                   'output': 'outputEstimates'}
        self.client.put(params_dict, 'params_dict')

    def _load_params_from_file(self, param_file):
        '''Filehandler for loading caiman parameters
            TODO
        '''
        return {}

    def putEstimates(self, estimates, output):
        ''' Put whatever estimates we currently have
            into the output location specified
            TODO rewrite output input
        '''
        t = time.time()
        nb = self.onAc.params.get('init', 'nb')
        A = self.onAc.estimates.Ab[:, nb:]
        before = 0#self.frame_number-500 if self.frame_number > 500 else 0
        C = self.onAc.estimates.C_on[nb:self.onAc.M, before:self.frame_number] #.get_ordered()
        t2 = time.time()
        if self.onAc.estimates.OASISinstances is not None:
            try:
                # if self.dropped_frames and self.dropped_frames[-1] > before: #Need to pad with zeros due to dropped/missing frames
                #     S = np.zeros((self.onAc.estimates.C_on.shape[0], self.frame_number - before)) #should always be 500 or TODO self.onAC.window
                #     print('osi.s shape ', self.onAc.estimates.OASISinstances[0].s.shape)
                #     if before < self.dropped_frames[0]:
                #         tmp = np.stack([osi.s[before:self.dropped_frames[0]] for osi in self.onAc.estimates.OASISinstances])
                #         S[:tmp.shape[0],:self.dropped_frames[0]-before] = tmp
                #     good_frames = np.array([f for f in range(before,self.frame_number,1) if f not in self.dropped_frames])
                #     if good_frames.shape[0] > 0:
                #         if good_frames[0] < self.onAc.estimates.OASISinstances[0].s.shape[0]: #may not have oasis for these frames yet
                #             tmp2 = np.stack([osi.s[good_frames] for osi in self.onAc.estimates.OASISinstances])
                #             S[:tmp2.shape[0], good_frames-before] = tmp2
                #         else: #TODO just for testing
                #             tmp2 = np.stack([osi.s[-good_frames.shape[0]:] for osi in self.onAc.estimates.OASISinstances])
                #             S[:tmp2.shape[0], good_frames-before] = tmp2
                #         # max_len = max([len(osi.s[before:self.frame_number]) for osi in self.onAc.estimates.OASISinstances])
                #         # S = np.array([np.lib.pad(osi.s[before:self.frame_number], (0, max_len-len(osi.s[before:self.frame_number])), 'constant', constant_values=0) for osi in self.onAc.estimates.OASISinstances])
                # else:
                S = np.stack([osi.s[before:self.frame_number] for osi in self.onAc.estimates.OASISinstances])    
            except IndexError:
                print('Index error!')
                # print('shape good frames ', good_frames.shape)       
                # print('good frames', good_frames)
                print('len dropped frames ', len(self.dropped_frames))
                # if tmp2: print('tmp2 shape', tmp2.shape)
                print(self.frame_number)
                print(before)         
        else:
            S = np.zeros((self.onAc.estimates.C_on.shape[0], self.frame_number - before))
        t3 = time.time()

        image = self.makeImage()
        if self.frame_number == 1:
            np.savetxt('image.txt', np.array(image))
        t4 = time.time()
        dims = image.shape
        self._updateCoords(A,dims)
        t5 = time.time()

        ids = []
        ids.append(self.client.put(self.coords, 'coords'+str(self.frame_number)))
        ids.append(self.client.put(image, 'proc_image'+str(self.frame_number)))
        ids.append(self.client.put(C, 'S'+str(self.frame_number)))
        ids.append(self.frame_number)
        t6 = time.time()
        self.q_out.put(ids)
        #self.q_comm.put([self.frame_number])

        self.putAnalysis_time.append([time.time()-t, t2-t, t3-t2, t4-t3, t5-t4, t6-t5])
    

    def _checkFrames(self):
        ''' Check to see if we have frames for processing
        '''
        try:
            res = self.q_in.get(timeout=0.0005)
            return res
        #TODO: add'l error handling
        except Empty:
            # logger.info('No frames for processing')
            return None


    def _processFrame(self, frame, frame_number):
        ''' Do some basic processing on a single frame
            Raises NaNFrameException if a frame contains NaN
            Returns the normalized/etc modified frame
        '''
        t=time.time()
        if frame is None:
            raise ObjectNotFoundError
        if np.isnan(np.sum(frame)):
            raise NaNFrameException
        frame = frame.astype(np.float32) #or require float32 from image acquistion
        if self.onAc.params.get('online', 'ds_factor') > 1:
            frame = cv2.resize(frame, self.onAc.img_norm.shape[::-1])
            # TODO check for params, onAc componenets before calling, or except
        if self.onAc.params.get('online', 'normalize'):
            frame -= self.onAc.img_min
        if self.onAc.params.get('online', 'motion_correct'):
            try:
                templ = self.onAc.estimates.Ab.dot(
                self.onAc.estimates.C_on[:self.onAc.M, (frame_number-1)]).reshape(
                # self.onAc.estimates.C_on[:self.onAc.M, (frame_number-1)%self.onAc.window]).reshape(
                self.onAc.params.get('data', 'dims'), order='F')*self.onAc.img_norm
            except Exception as e:
                logger.error('Unknown exception {0}'.format(e))
                raise Exception
            
            if self.onAc.params.get('motion', 'pw_rigid'):
                frame_cor, shift, _, xy_grid = tile_and_correct(frame, templ, self.onAc.params.motion['strides'], self.onAc.params.motion['overlaps'],
                                                                            self.onAc.params.motion['max_shifts'], newoverlaps=None, newstrides=None, upsample_factor_grid=4,
                                                                            upsample_factor_fft=10, show_movie=False, max_deviation_rigid=self.onAc.params.motion['max_deviation_rigid'],
                                                                            add_to_movie=0, shifts_opencv=True, gSig_filt=None,
                                                                            use_cuda=False, border_nan='copy')
            else:
                frame_cor, shift = motion_correct_iteration_fast(frame, templ, self.max_shifts_online, self.max_shifts_online)
            self.onAc.estimates.shifts.append(shift)
        else:
            frame_cor = frame
        if self.onAc.params.get('online', 'normalize'):
            frame_cor = frame_cor/self.onAc.img_norm
        self.procFrame_time.append([time.time()-t])
        return frame_cor


    def _fitFrame(self, frame_number, frame):
        ''' Do the heavy lifting here. CNMF, etc
            Updates self.onAc.estimates
        '''
        try:
            self.onAc.fit_next(frame_number, frame)
        except Exception as e:
            logger.error('Fit frame error! {}: {}'.format(type(e).__name__, e))
            raise Exception


    def _updateCoords(self, A, dims):
        '''See if we need to recalculate the coords
           Also see if we need to add components
        '''
        if self.coords is None: #initial calculation
            self.A = A
            self.coords = get_contours(A, dims)

        elif np.shape(A)[1] > np.shape(self.A)[1] and self.frame_number % 50 == 0: 
            #Only recalc if we have new components
            # FIXME: Since this is only for viz, only do this every 100 frames
            # TODO: maybe only recalc coords that are new? 
            self.A = A
            self.coords = get_contours(A, dims)
            self.counter += 1


    def makeImage(self):
        '''Create image data for visualiation
            Using caiman code here
            #TODO: move to MeanAnalysis class ?? Check timing if we move it!
                Other idea -- easier way to compute this?
        '''
        mn = self.onAc.M - self.onAc.N
        image = None
        try:
            # components = self.onAc.estimates.Ab[:,mn:].dot(self.onAc.estimates.C_on[mn:self.onAc.M,(self.frame_number-1)%self.onAc.window]).reshape(self.onAc.dims, order='F')
            # background = self.onAc.estimates.Ab[:,:mn].dot(self.onAc.estimates.C_on[:mn,(self.frame_number-1)%self.onAc.window]).reshape(self.onAc.dims, order='F')
            components = self.onAc.estimates.Ab[:,mn:].dot(self.onAc.estimates.C_on[mn:self.onAc.M,(self.frame_number-1)]).reshape(self.onAc.dims, order='F')
            background = self.onAc.estimates.Ab[:,:mn].dot(self.onAc.estimates.C_on[:mn,(self.frame_number-1)]).reshape(self.onAc.dims, order='F')
            image = ((components + background) - self.onAc.bnd_Y[0])/np.diff(self.onAc.bnd_Y)
            image = np.minimum((image*255.),255).astype('u1')
        except ValueError as ve:
            logger.info('ValueError: {0}'.format(ve))

        #cor_frame = (self.frame - self.onAc.bnd_Y[0])/np.diff(self.onAc.bnd_Y)

        return image

class NaNFrameException(Exception):
    pass








