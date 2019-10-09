import time
import os
import h5py
import struct
import numpy as np
import random

from pathlib import Path
from skimage.external.tifffile import imread
from nexus.actor import Actor, Spike, RunManager
from queue import Empty

import logging; logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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
        np.savetxt('timing/acquire_frame_time.txt', np.array(self.total_times))
        np.savetxt('timing/acquire_timestamp.txt', np.array(self.timestamp))

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
            if self.frame_num > 2000 and self.frame_num < 2800:
                frame = None
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
        ''' Can be live acquistion from disk (?) #TODO
            Here just return frame from loaded data
        '''
        return self.data[num,:,:]

    def saveFrame(self, frame):
        ''' TODO: this
        '''
        pass
        # self.dset[self.frame_num-1] = frame
        # self.f.flush()

class TbifAcquirer(FileAcquirer):
    def setup(self):
        if os.path.exists(self.filename):
            print('Looking for ', self.filename)
            n, ext = os.path.splitext(self.filename)[:2]
            if ext == '.tbif':
                self.data = []
                self.stim = []
                self.zpos = []
                with open(self.filename, mode='rb') as f:
                    data = f.read()
                    header = struct.unpack("=IdHHffffdd", data[0:48])
                    #res is: fpp, spf, w, h, 
                    print('loading : ', header)
                    img_size = header[2]*header[3]
                    dt = np.dtype('uint16')
                    # -------- repeats here, starts at 48, read 4, 12, img_size
                    for i in range(0,2878):
                        zpos, = struct.unpack("=f", data[48+(16+img_size*2)*i:52+(16+img_size*2)*i])
                        self.zpos.append(zpos)
                        stim = struct.unpack("=fff", data[52+(16+img_size*2)*i:64+(16+img_size*2)*i])
                        self.stim.append(np.asarray(stim))
                        img = struct.unpack("="+str(img_size)+"H", data[64+(16+img_size*2)*i:64+img_size*2+(16+img_size*2)*i])
                        tmp = np.reshape(np.asarray(img, dtype='uint16'), (header[2], header[3]), order='F')
                        self.data.append(tmp.transpose())
                    self.data = np.array(self.data)
                    # self.stim = np.array(self.stim)
                    # np.savetxt('stim_data.txt', self.stim)
                    print('data is ', len(self.data))
            else: 
                logger.error('Cannot load file, bad extension')
                raise Exception
        else: raise FileNotFoundError

    def runAcquirer(self):
        t = time.time()

        if self.done:
            pass 
        elif(self.frame_num < len(self.data)):
            frame = self.getFrame(self.frame_num)
            if self.frame_num == len(self.data):
                print('Done with first set ', self.frame_num)
            # if self.frame_num > 1000 and self.frame_num < 2000:
            #     frame = None
            id = self.client.put(frame, 'acq_raw'+str(self.frame_num))
            self.timestamp.append([time.time(), self.frame_num])
            try:
                self.q_out.put([{str(self.frame_num):id}])
                self.links['stim_queue'].put({self.frame_num:self.stim[self.frame_num % len(self.stim)]})
                #logger.info('Current stim: {}'.format(self.stim[self.frame_num]))
                self.frame_num += 1
                self.saveFrame(frame) #also log to disk #TODO: spawn separate process here?     
            except Exception as e:
                logger.error('Acquirer general exception: {}'.format(e))

            time.sleep(self.framerate) #pretend framerate

        else:
            logger.error('Done with all available frames: {0}'.format(self.frame_num))
            self.data = None
            self.q_comm.put(None)
            self.done = True

        self.total_times.append(time.time()-t)

    def getFrame(self, num):
        '''
            Here just return frame from loaded data
        '''
        if num >= len(self.data):
            num = num % len(self.data)
        return self.data[num,:,:]


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
        #Faking it for now. TODO: Talk to Max about his format
        if self.n % 100 == 0:
            self.curr_stim = random.choice(self.behaviors)
        self.onoff = random.choice([0,20])
        self.q_out.put({self.n:[self.curr_stim, self.onoff]})
        #logger.info('Changed stimulus! {}'.format(self.curr_stim))
        #self.q_comm.put()
        time.sleep(0.068)
        self.n += 1


class FolderAcquirer(Actor):
    ''' TODO: Current behavior is looping over all files in a folder.
    Class to read TIFF files in a specified {path} from disk.
    Designed for scenarios when new TIFF files are created during the run.
    Reads only new TIFF files (after Run started) and put on to the Plasma store.
    If there're multiple files, files are loaded by name.
    '''

    def __init__(self, *args, folder=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = None
        self.done = False
        self.flag = False
        self.path = Path(folder)

        self.frame_num = 0
        self.files = set()

        if not self.path.exists() or not self.path.is_dir():
            raise AttributeError(f'Folder {self.path} does not exist.')

    def setup(self):
        pass
        
    def saveImgs(self):
        self.imgs = []
        files = {f for f in self.path.iterdir() if f.suffix in ['.tif', '.tiff']}
        files = sorted(list(files))
        for file in files:
            img = self.get_tiff(file)
            self.imgs.append(img)
        self.imgs = np.array(self.imgs)
        f = h5py.File('data/sample.h5', 'w', libver='latest')
        f.create_dataset("default", data=self.imgs)
        f.close()

    def run(self):
        '''Triggered at Run
           Get list of files in the folder and use that as the baseline.
        '''
        self.total_times = []
        self.timestamp = []

        self.files = {f for f in self.path.iterdir() if f.suffix in ['.tif', '.tiff']}

        with RunManager(self.name, self.runAcquirer, self.setup, self.q_sig, self.q_comm) as rm:
            print(rm)

        print('Acquire broke, avg time per frame: ', np.mean(self.total_times))
        print('Acquire got through ', self.frame_num, ' frames')
        np.savetxt('timing/acquire_frame_time.txt', self.total_times)
        np.savetxt('timing/acquire_timestamp.txt', self.timestamp)

    def runAcquirer(self):
        ''' Main loop. If there're new files, read and put into store.
        '''
        t = time.time()
        files_current = {f for f in self.path.iterdir() if f.suffix in ['.tif', '.tiff']}
        # files_new = files_current - self.files
        files_new = files_current  # TODO Remove before use.

        if len(files_new) == 0:
            time.sleep(0.01) #TODO: Remove before use

        else:  # New files
            files_new = sorted(list(files_new))
            for file in files_new:
                obj_id = self.client.put(self.get_tiff(file), 'acq_raw' + str(self.frame_num))
                self.q_out.put([{str(self.frame_num): obj_id}])
                self.frame_num += 1
                self.files.add(file)
                # time.sleep(0.1)  # TODO Remove before use.

            self.total_times.append(time.time() - t)

    def get_tiff(self, file: Path):
        try:
            img = imread(file.as_posix())
        except ValueError as e:
            img = imread(file.as_posix())
            logger.error('File '+file.as_posix()+' had value error {}'.format(e))
        return img #[0,0,0, :, :,0]  #Extract first channel in this image set. #TODO: Likely change this


if __name__ == '__main__':
    FA = FolderAcquirer('FA', folder='data/duke_exp/2019/10/07/1')
    FA.saveImgs()