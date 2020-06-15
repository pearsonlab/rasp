import time
import os
import h5py
import random
from queue import Empty
import numpy as np
from skimage.external.tifffile import imread
from improv.actor import Actor, Spike, RunManager

import logging; logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Classes: File Acquirer, Stim, Behavior, Tiff

class FileAcquirer(Actor):
    '''Class to import data from files and output
       frames in a buffer, or discrete.
    '''
    def __init__(self, *args, filename=None, framerate=30, **kwargs):
        super().__init__(*args, **kwargs)
        self.frame_num = 0
        self.data = None
        self.done = False
        self.flag = False
        self.filename = filename
        self.framerate = 1/framerate 

    def setup(self):
        '''Get file names from config or user input
            Also get specified framerate, or default is 10 Hz
           Open file stream
           #TODO: implement more than h5 files
        '''        
        print('Looking for ', self.filename)
        if os.path.exists(self.filename):
            n, ext = os.path.splitext(self.filename)[:2]
            if ext == '.h5' or ext == '.hdf5':
                with h5py.File(self.filename, 'r') as file:
                    keys = list(file.keys())
                    self.data = file[keys[0]].value #only one dset per file atm
                        #frames = np.array(dset).squeeze() #not needed?
                    print('data is ', len(self.data))

        else: raise FileNotFoundError

        # save_file = self.filename.split('.')[0]+'_backup'+'.h5' #TODO: make parameter in setup ?
        # self.f = h5py.File(save_file, 'w', libver='latest')
        # self.dset = self.f.create_dataset("default", (len(self.data),)) #TODO: need to set maxsize to none?

    def run(self):
        ''' Run indefinitely. Calls runAcquirer after checking for singals
        '''
        self.total_times = []
        self.timestamp = []

        with RunManager(self.name, self.runAcquirer, self.setup, self.q_sig, self.q_comm) as rm:
            print(rm)            
            
        print('Acquire broke, avg time per frame: ', np.mean(self.total_times))
        print('Acquire got through ', self.frame_num, ' frames')
        np.savetxt('output/timing/acquire_frame_time.txt', np.array(self.total_times))
        np.savetxt('output/timing/acquire_timestamp.txt', np.array(self.timestamp))

    def runAcquirer(self):
        '''While frames exist in location specified during setup,
           grab frame, save, put in store
        '''
        t = time.time()

        if self.done:
            pass #logger.info('Acquirer is done, exiting')
            #return
        elif(self.frame_num < len(self.data)*3000):
            frame = self.getFrame(self.frame_num % len(self.data))
            # if self.frame_num > 1500 and self.frame_num < 1800:
            #     frame = None
            id = self.client.put(frame, 'acq_raw'+str(self.frame_num))
            self.timestamp.append([time.time(), self.frame_num])
            try:
                self.q_out.put([{str(self.frame_num):id}])
                self.frame_num += 1
                self.saveFrame(frame) #also log to disk #TODO: spawn separate process here?     
            except Exception as e:
                logger.error('Acquirer general exception: {}'.format(e))

            time.sleep(self.framerate) #pretend framerate
            self.total_times.append(time.time()-t)

        else: # essentially a done signal from the source (eg, camera)
            logger.error('Done with all available frames: {0}'.format(self.frame_num))
            self.data = None
            self.q_comm.put(None)
            self.done = True
            #self.f.close()
    
    def getFrame(self, num):
        ''' Here just return frame from loaded data
        '''
        return self.data[num,:,:]

    def saveFrame(self, frame):
        ''' Uncomment to save frame via h5 dset
            TODO: Test timing
        '''
        # self.dset[self.frame_num-1] = frame
        # self.f.flush()
        pass

class StimAcquirer(Actor):

    def __init__(self, *args, param_file=None, filename=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.param_file = param_file
        self.filename= filename

    def setup(self):
        self.n= 0
        if os.path.exists(self.filename):
            print('Looking for ', self.filename)
            n, ext = os.path.splitext(self.filename)[:2]
            if ext== ".txt":
                self.stim=[]
                f= np.loadtxt(self.filename)
                for i, frame in enumerate(f):
                    stiminfo= frame[0:2]
                    self.stim.append(stiminfo)
            else: 
                logger.error('Cannot load file, bad extension')
                raise Exception

        else: raise FileNotFoundError
        
    def run(self):
        ''' Run continuously, waiting for input
        '''
        with RunManager(self.name, self.getInput, self.setup, self.q_sig, self.q_comm) as rm:
            logger.info(rm)

    def getInput(self):
        ''' Check for input from behavioral control
        '''
        if (self.n<len(self.stim)):
            self.q_out.put({self.n:self.stim[self.n]})
        time.sleep(0.068)
        self.n+=1


class BehaviorAcquirer(Actor):
    ''' Actor that acquires information of behavioral stimulus
        during the experiment

        Current assumption is that stimulus is off or on, on has many types,
        and any change in stimulus is _un_associated with a frame number.
        TODO: needs to be associated with time, then frame number
    '''

    def __init__(self, *args, param_file=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.param_file = param_file

    def setup(self):
        ''' Pre-define set of input stimuli
        '''
        self.n = 0 #our fake frame number here
        #TODO: Consider global frame_number in store...or signal from Nexus

        #TODO: Convert this to Tweak and load from there
        if self.param_file is not None:
            try:
                params_dict = None #self._load_params_from_file(param_file)
            except Exception as e:
                logger.exception('File cannot be loaded. {0}'.format(e))
        else:
            self.behaviors = [0, 1, 2, 3, 4, 5, 6, 7] #8 sets of input stimuli

    def run(self):
        ''' Run continuously, waiting for input
        '''
        with RunManager(self.name, self.getInput, self.setup, self.q_sig, self.q_comm) as rm:
            logger.info(rm)

    def getInput(self):
        ''' Check for input from behavioral control
        '''
        #Faking it for now.
        if self.n % 100 == 0:
            self.curr_stim = random.choice(self.behaviors)
            self.onoff = random.choice([0,20])
            self.q_out.put({self.n:[self.curr_stim, self.onoff]})
        #logger.info('Changed stimulus! {}'.format(self.curr_stim))
        #self.q_comm.put()
        time.sleep(0.068)
        self.n += 1


class TiffAcquirer(Actor):
    ''' Loops through a TIF file.
    '''

    def __init__(self, *args, filename=None, framerate=30, **kwargs):
        super().__init__(*args, **kwargs)
        self.filename = filename

        if not os.path.exists(filename):
            raise ValueError('TIFF file {} does not exist.'.format(filename))
        self.imgs = np.array(0)

        self.n_frame = 0
        self.fps = framerate

        self.t_per_frame = list()

    def setup(self):
        self.imgs = imread(self.filename)

    def run(self):
        with RunManager(self.name, self.run_acquirer, self.setup, self.q_sig, self.q_comm) as rm:
            print(rm)

    def run_acquirer(self):
        t0 = time.time()

        id_store = self.client.put(self.imgs[self.n_frame % len(self.imgs), ...], 'acq_raw' + str(self.n_frame))
        self.q_out.put([{str(self.n_frame): id_store}])
        self.n_frame += 1

        time.sleep(1 / self.fps)

        self.t_per_frame.append(time.time() - t0)
