import time
import pickle
import cv2
import numpy as np
import scipy.sparse
from nexus.store import Limbo
from caiman.source_extraction import cnmf
from caiman.source_extraction.cnmf.online_cnmf import OnACID
from caiman.source_extraction.cnmf.params import CNMFParams
from caiman.motion_correction import motion_correct_iteration_fast, tile_and_correct
import caiman as cm
import logging; logger = logging.getLogger(__name__)


class Processor():
    '''Abstract class for the processor component
       Needs to take an image from data store (DS)
       Needs to output spikes estimates over time
       Will likely change specifications in the future
    '''
    
    def setupProcess(self):
        # Essenitally the registration process
        raise NotImplementedError

    def runProcess(self):
        # Get image and then process b/t image and estimates
        raise NotImplementedError
    
    def putAnalysis(self):
        # Update the DS with estimates
        raise NotImplementedError



class CaimanProcessor(Processor):
    '''Wraps CaImAn/OnACID functionality to
       interface with our pipeline.
    '''

    def __init__(self, name, client):
        self.name = name
        self.client = client
        self.ests = None

    def __str__(self):
        return self.name

    def setStore(self, client):
        self.client = client
    
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
            # TODO add parameter validation inside Tweak perhaps
            params_dict = {'fnames': ['/Users/hawkwings/Documents/Neuro/RASP/rasp/data/Tolias_mesoscope_1.hdf5', '/Users/hawkwings/Documents/Neuro/RASP/rasp/data/Tolias_mesoscope_2.hdf5'],
                   'fr': 15,
                   'decay_time': 0.5,
                   'gSig': (3,3),
                   'p': 1,
                   'min_SNR': 1,
                   'rval_thr': 0.9,
                   'ds_factor': 1,
                   'nb': 2,
                   'motion_correct': True,
                   'init_batch': 200,
                   'init_method': 'bare',
                   'normalize': True,
                   'sniper_mode': False,
                   'K': 2,
                   'epochs': 1,
                   'max_shifts_online': np.ceil(10).astype('int'),
                   'pw_rigid': False,
                   'dist_shape_update': True,
                   'min_num_trial': 10,
                   'show_movie': False,
                   'output': 'outputEstimates'}
        self.client.put(params_dict, 'params_dict')
        print('put dict into limbo')
    

    def _load_params_from_file(self, param_file):
        return {}


    def setupProcess(self):
        ''' Create OnACID object and initialize it
            limboClient is a client to the data store server
            Future option: put configParams in store and load here
        '''

        # TODO self.loadParams(param_file)
        self.loadParams()
        self.params = self.client.get('params_dict')
        print('Using parameters:', self.params)
        
        # MUST include inital set of frames
        # Institute check here as requirement to Nexus
        
        self.opts = CNMFParams(params_dict=self.params)
        self.onAc = OnACID(params = self.opts)
        self.frame_number = self.params['init_batch']
        self.onAc.initialize_online()
        self.max_shifts_online = self.onAc.params.get('online', 'max_shifts_online')

        return self

    def runProcess(self):
        ''' Run process. Persists running while it has data
            NOT IMPLEMENTED. Runs once atm. Add new function
            to run continually.
            Frames is a location in the DS that this process
            needs to check for more data
            Output is a location in the DS to continually
            place the Estimates results, with ref number that
            corresponds to the frame number
        '''
        print('Running process beginning with ', self.frame_number)
        proc_params = self.client.get('params_dict')
        print('got parameter dict: ', proc_params)
        fnames = proc_params['fnames']
        output = proc_params['output']
        self.fnames = self._checkFrames(fnames)
        print('fnames is ', self.fnames)
        if self.fnames is not None:
            # still more to process
            init_batch = [self.params['init_batch']]+[0]*(len(self.fnames)-1)
            #print('init batch is ', init_batch)
            #init_batch = [0]*len(self.fnames)
            #frame_number = init_batch[0]
            for file_count, ffll in enumerate(self.fnames):
                print('Loading file:', ffll, ' current frame ', self.frame_number)
                Y = cm.load(ffll, subindices=slice(init_batch[file_count], None, None))
                # TODO replace load
                for frame_count, frame in enumerate(Y):
                    frame = self._processFrame(frame, self.frame_number)
                    self._fitFrame(self.frame_number, frame.reshape(-1, order='F'))
                    if frame_count % 10 == 0: self.putAnalysis(self.onAc.estimates, output) # currently every frame. User-specified?
                    self.frame_number += 1
            if self.onAc.params.get('online', 'normalize'):
                # normalize final estimates for this set of files. Useful?
                #self._normAnalysis()  #WARNING CANT LOOP
                self.putAnalysis(self.onAc.estimates, output)
            #self._finalAnalysis(frame_number)
            #self.putAnalysis(self.finalEstimates, output)
        
        #once runProcess has run once, need to reset init_batch to avoid internal errors
        #currently not logging this change; keeping all internal to caiman
        self.onAc.params.set('online', {'init_batch': 0})
        self.params['init_batch'] = 0
        # also need to extend dimensions of timesteps...TODO: better method init?


        #TODO: determine a SINGLE location for params. Internal vs logged?
        #self.client.replace(self.params, 'params_dict')
        logger.info('Updated init batch after first run')


    def putAnalysis(self, estimates, output):
        ''' Put whatever estimates we currently have
            into the output location specified
            TODO rewrite output input
        '''
        # Just store dF/F traces for now
        # can also use utils function directly vs
        # calling from Estimates class
        #   dF = estimates.detrend_df_f(frames_window=100).F_dff
        #currEstimates = pickle.dumps(self.onAc.estimates.__dict__)
            # TODO replace above with translator to panda DF?
        #   self.client.replace(dF, output)
        self.ests = estimates.C_on

    def getEstimates(self):
        return self.ests
    
    def getTime(self):
        return self.frame_number

    def _finalAnalysis(self, t):
        ''' Some kind of final steps for estimates
            t is the final frame count
            TODO: get params from elsewhere in case changed!
            Can't put these into onAc.estimates since it changes shape,
            and thus interferes with running the process again in a loop.
        '''
        #TODO change epochs?
        epochs = 1

        self.finalEstimates = self.onAc.estimates
        
        self.finalEstimates.A, self.finalEstimates.b = self.onAc.estimates.Ab[:, self.onAc.params.get('init', 'nb'):], self.onAc.estimates.Ab[:, :self.onAc.params.get('init', 'nb')].toarray()
        self.finalEstimates.C, self.finalEstimates.f = self.onAc.estimates.C_on[self.onAc.params.get('init', 'nb'):self.onAc.M, t - t //
                         epochs:t], self.onAc.estimates.C_on[:self.onAc.params.get('init', 'nb'), t - t // epochs:t]
        noisyC = self.onAc.estimates.noisyC[self.onAc.params.get('init', 'nb'):self.onAc.M, t - t // epochs:t]
        self.finalEstimates.YrA = noisyC - self.onAc.estimates.C
        self.finalEstimates.bl = [osi.b for osi in self.onAc.estimates.OASISinstances] if hasattr(self, 'OASISinstances') else [0] * self.onAc.estimates.C.shape[0]
        self.finalEstimates.C_on = self.onAc.estimates.C_on[:self.onAc.M]
        self.finalEstimates.noisyC = self.onAc.estimates.noisyC[:self.onAc.M]



    def _checkFrames(self, fnames):
        ''' Check to see if we have frames for processing
        '''
        return fnames


    def _processFrame(self, frame, frame_number):
        ''' Do some basic processing on a single frame
            Raises NaNFrameException if a frame contains NaN
            Returns the normalized/etc modified frame
        '''

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
                self.onAc.estimates.C_on[:self.onAc.M, frame_number-1]).reshape(
                self.onAc.params.get('data', 'dims'), order='F')*self.onAc.img_norm
            except Exception as e:
                logger.error('Unknown exception {0}'.format(e))
                raise Exception
            
            if self.onAc.params.get('motion', 'pw_rigid'):
                frame_cor1, shift = motion_correct_iteration_fast(
                            frame, templ, self.max_shifts_online, self.max_shifts_online)
                frame_cor, shift = tile_and_correct(frame, templ, self.onAc.params.motion['strides'], self.onAc.params.motion['overlaps'], onAc.params.motion['max_shifts'], newoverlaps=None, newstrides=None, upsample_factor_grid=4, upsample_factor_fft=10, show_movie=False, max_deviation_rigid=onAc.params.motion['max_deviation_rigid'],add_to_movie=0, shifts_opencv=True, gSig_filt=None, use_cuda=False, border_nan='copy')[:2]
            else:
                frame_cor, shift = motion_correct_iteration_fast(frame, templ, self.max_shifts_online, self.max_shifts_online)
            self.onAc.estimates.shifts.append(shift)
        else:
            #templ = None
            frame_cor = frame
        if self.onAc.params.get('online', 'normalize'):
            frame_cor = frame_cor/self.onAc.img_norm
    
        return frame_cor



    def _fitFrame(self, frame_number, frame):
        ''' Do the heavy lifting here. CNMF, etc
            Updates self.onAc.estimates
        '''
        try:
            self.onAc.fit_next(frame_number, frame)
        except Exception as e:
            #print('error likely due to frame number ', frame_number)
            print('Message: {0}'.format(e))
            raise Exception


    def _normAnalysis(self):
        self.onAc.estimates.Ab /= 1./self.onAc.img_norm.reshape(-1, order='F')[:,np.newaxis]
        self.onAc.estimates.Ab = scipy.sparse.csc_matrix(self.onAc.estimates.Ab)


class NaNFrameException(Exception):
    pass








