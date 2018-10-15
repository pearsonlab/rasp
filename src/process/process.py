import time
from nexus.store import Limbo
from caiman.online_cnmf import OnACID
from caiman.params import CNMFParams
import caiman as cm
import logging; logger = logging.getLogger(__name__)


class Processor(object):
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

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def setupProcess(self, limboClient, params):
        ''' Create OnACID object and initialize it
            limboClient is a client to the data store server
            params is an object_name to return a dict
            Future option: put configParams in store and load here
        '''

        self.client = limboClient
        self.params = self.client.get(params)
        # MUST include inital set of frames
        # Institute check here as requirement to Nexus
        
        self.opts = CNMFParams(params_dict=self.params)
        self.onAc = OnACID(params = self.opts)
        self.onAC.initialize_online()


    def runProcess(self, frames, output):
        ''' Run process. Persists running while it has data
            NOT IMPLEMENTED. Runs once atm. Add new function
            to run continually.
            Frames is a location in the DS that this process
            needs to check for more data
            Output is a location in the DS to continually
            place the Estimates results, with ref number that
            corresponds to the frame number
        '''
        self.frames = self.checkFrames(frames)
        if self.frames is not None:
            # still more to process
            init_batch = [self.params.init_batch]+[0]*(len(self.frames)-1)
            frame_number = 1
            for file_count, ffll in enumerate(self.frames)
                Y = cm.load(ffll, subindices=slice(init_batch, None, None))
                # TODO replace load
                for frame_count, frame in enumerate(Y):
                    frame = self._processFrame(frame)
                    self._fitFrame(frame_number, frame.reshape(-1, order='F'))
                    self.putAnalysis(ouput) # currently every frame. User-specified?
                if self.onAc.params.get('online', 'normalize'):
                    # normalize final estimates for this file. Useful?
                    self._normAnalysis()
                    self.putAnalysis(output)
                frame_number += 1


    def putAnalysis(self, output):
        ''' Put whatever estimates we currently have
            into the output location specified
            TODO rewrite output input (lol)
        '''
        currEstimates = self.onAc.estimates
            # TODO replace above with translator to panda DF?
            # so can put into DS
        self.client.put(output, currEstimates)


    def _processFrame(self, frame):
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
                self.onAc.estimates.C_on[:self.onAc.M, ind-1]).reshape(
                self.onAc.params.get('data', 'dims'), order='F')*self.onAc.img_norm
            except Exception as e:
                logger.error('Unknown exception {0}'.format(e))
            
            if self.onAc.params.get('motion', 'pw_rigid')
                frame_cor1, shift = motion_correct_iteration_fast(
                            frame, templ, max_shifts_online, max_shifts_online)
                frame_cor, shift = tile_and_correct(frame, templ, onAc.params.motion['strides'], onAc.params.motion['overlaps'], onAc.params.motion['max_shifts'], newoverlaps=None, newstrides=None, upsample_factor_grid=4, upsample_factor_fft=10, show_movie=False, max_deviation_rigid=onAc.params.motion['max_deviation_rigid'],add_to_movie=0, shifts_opencv=True, gSig_filt=None, use_cuda=False, border_nan='copy')[:2]
            else:
                frame_cor, shift = motion_correct_iteration_fast(frame, templ, max_shifts_online, max_shifts_online)
            onAc.estimates.shifts.append(shift)
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
        self.onAc.fit_next(frame_number, frame)


class NaNFrameException(Exception):
    pass








