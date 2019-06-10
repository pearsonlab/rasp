import time
import os
import h5py
import numpy as np
import random
from nexus.module import Module, Spike, RunManager
from queue import Empty

import logging; logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Acquirer(Module):
    '''Abstract class for the image acquirer component
       Needs to obtain an image from some input (eg, microscope, file)
       Needs to output frames standardized for processor. Can do some normalization
       Also saves direct to disk in parallel (?)
       Will likely change specifications in the future
    '''
    #def getFrame(self):
    #    # provide function for grabbing the next single frame
    #    raise NotImplementedError
    # TODO: require module-specific functions or no?


class FileAcquirer(Acquirer):
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
        #self.lower_priority = True

        if os.path.exists(self.filename):
            print('Looking for ', self.filename)
            n, ext = os.path.splitext(self.filename)[:2]
            if ext == '.h5' or ext == '.hdf5':
                with h5py.File(self.filename, 'r') as file:
                    keys = list(file.keys())
                    self.data = file[keys[0]].value #only one dset per file atm
                        #frames = np.array(dset).squeeze() #not needed?
                    print('data is ', len(self.data))
        else: raise FileNotFoundError

        save_file = self.filename.split('.')[0]+'_backup'+'.h5' #TODO: make parameter in setup ?
        self.f = h5py.File(save_file, 'w', libver='latest')
        self.dset = self.f.create_dataset("default", (len(self.data),)) #TODO: need to set maxsize to none?

    def getFrame(self, num):
        ''' Can be live acquistion from disk (?) #TODO
            Here just return frame from loaded data
        '''
        return self.data[num,:,:]

    def run(self):
        ''' Run indefinitely. Calls runAcquirer after checking for singals
        '''
        self.total_times = []

        with RunManager(self.runAcquirer, self.setup, self.q_sig, self.q_comm) as rm:
            print(rm)

        # #self.changePriority() #run once, at start of process
        # while True:
        #     t = time.time()
        #     if self.flag:
        #         try:
        #             self.runAcquirer()
        #         except Exception as e:
        #             logger.error('Acquirer exception during run: {}'.format(e))
        #             #break 
        #     try: 
        #         signal = self.q_sig.get(timeout=0.005)
        #         if signal == Spike.run(): 
        #             self.flag = True
        #             logger.warning('Received run signal, begin running acquirer')
        #         elif signal == Spike.quit():
        #             logger.warning('Received quit signal, aborting')
        #             break
        #         elif signal == Spike.pause():
        #             logger.warning('Received pause signal, pending...')
        #             self.flag = False
        #         elif signal == Spike.resume(): #currently treat as same as run
        #             logger.warning('Received resume signal, resuming')
        #             self.flag = True
        #     except Empty as e:
        #         pass #no signal from Nexus
            
            
        print('Acquire broke, avg time per frame: ', np.mean(self.total_times))
        print('Acquire got through ', self.frame_num, ' frames')

    def runAcquirer(self):
        '''While frames exist in location specified during setup,
           grab frame, save, put in store
        '''
        t = time.time()

        if self.done:
            pass #logger.info('Acquirer is done, exiting')
            #return
        elif(self.frame_num < len(self.data)):
            frame = self.getFrame(self.frame_num)
            id = self.client.put(frame, str(self.frame_num))
            try:
                self.q_out.put([{str(self.frame_num):id}])
                #self.q_comm.put([self.frame_num]) #TODO: needed?
                self.frame_num += 1

                self.saveFrame(frame) #also log to disk #TODO: spawn separate process here?               
            except Exception as e:
                logger.error('Acquirer general exception: {}'.format(e))

            time.sleep(self.framerate) #pretend framerate

        else: # essentially a done signal from the source (eg, camera)
            logger.error('Done with all available frames: {0}'.format(self.frame_num))
            self.data = None
            self.q_out.put(None)
            self.q_comm.put(None)
            self.done = True
            self.f.close()

        self.total_times.append(time.time()-t)


    def saveFrame(self, frame):
        ''' TODO: this
        '''
        pass
        # self.dset[self.frame_num-1] = frame
        # self.f.flush()


class BehaviorAcquirer(Module):
    ''' Module that acquires information of behavioral stimulus
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
            self.behaviors = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] #10 sets of input stimuli

    def run(self):
        ''' Run continuously, waiting for input
        '''
        with RunManager(self.getInput, self.setup, self.q_sig, self.q_comm) as rm:
            logger.info(rm)
        # while True:
        #     if self.flag:
        #         try:
        #             self.getInput()
        #             if self.done:
        #                 logger.info('BehaviorAcquirer is done, exiting')
        #                 return
        #         except Exception as e:
        #             logger.error('BehaviorAcquirer exception during run: {}'.format(e))
        #             break 
        #     try: 
        #         signal = self.q_sig.get(timeout=0.005)
        #         if signal == Spike.run(): 
        #             self.flag = True
        #             logger.warning('Received run signal, begin running')
        #         elif signal == Spike.quit():
        #             logger.warning('Received quit signal, aborting')
        #             break
        #         elif signal == Spike.pause():
        #             logger.warning('Received pause signal, pending...')
        #             self.flag = False
        #         elif signal == Spike.resume(): #currently treat as same as run
        #             logger.warning('Received resume signal, resuming')
        #             self.flag = True
        #     except Empty as e:
        #         pass #no signal from Nexus

    def getInput(self):
        ''' Check for input from behavioral control
        '''
        #Faking it for now. TODO: Talk to Max about his format
        if self.n % 500 == 0:
            self.curr_stim = random.choice(self.behaviors)
            self.q_out.put({self.n:self.curr_stim})
            logger.warning('Changed stimulus! {}'.format(self.curr_stim))
            #self.q_comm.put()

        self.n += 1

