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
            time.sleep(5)
            self.q_comm.put([Spike.quit()])
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
        return self.data[num,:,:] #30:470,:]

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
        time.sleep(0.333)
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
            logger.error(
                'File '+file.as_posix()+' had value error {}'.format(e))
        return img #[0,0,0, :, :,0]  #Extract first channel in this image set. #TODO: Likely change this

import ipaddress
import zmq
import json

class ZMQAcquirer(Actor):

    def __init__(self, *args, ip=None, port=None, topicfilter=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ip = ip
        self.port = port
        self.topicfilter = topicfilter
        self.frame_num = 0

        # Sanity check
        # ipaddress.ip_address(self.ip)  # Check if IP is valid.
        # if not 0 <= port <= 65535:
        #     raise ValueError(f'Port {self.port} invalid.')

        # self.context = zmq.Context()
        # self.socket = self.context.socket(zmq.SUB)
        # self.socket.connect(f"tcp://{self.ip}:{self.port}")
        # self.socket.setsockopt_string(zmq.SUBSCRIBE, self.topicfilter)

    def setup(self):
        context = zmq.Context()
        self.socket = context.socket(zmq.SUB)
        self.socket.connect("tcp://10.122.170.21:4701")
        self.socket.connect("tcp://10.122.170.21:4702")
        self.socket.setsockopt(zmq.SUBSCRIBE, b'')

        self.saveArray = []

    def run(self):
        '''Triggered at Run
        '''
        self.total_times = []
        self.timestamp = []
        self.stimmed = []
        self.frametimes = []

        with RunManager(self.name, self.runAcquirer, self.setup, self.q_sig, self.q_comm) as rm:
            print(rm)

        self.imgs = np.array(self.saveArray)
        f = h5py.File('data/sample_stream.h5', 'w', libver='latest')
        f.create_dataset("default", data=self.imgs)
        f.close()

        np.savetxt('./stimmed.txt', np.array(self.stimmed))
        np.savetxt('./frametimes.txt', np.array(self.frametimes))

        print('Acquire broke, avg time per frame: ', np.mean(self.total_times))
        print('Acquire got through ', self.frame_num, ' frames')
        np.savetxt('timing/acquire_frame_time.txt', self.total_times)
        np.savetxt('timing/acquire_timestamp.txt', self.timestamp)

    def runAcquirer(self):
        ''' Main loop. If there're new files, read and put into store.
        '''
        t = time.time()
        #TODO: use poller instead to prevent blocking, include a timeout
        try:
            msg = self.socket.recv(flags=zmq.NOBLOCK)
            msg_parts = [part.strip() for part in msg.split(b': ', 1)]
            tag = msg_parts[0].split(b' ')[0]

            if tag == b'stimid':
                print('stimulus id: {}'.format(msg_parts[1]))
                # output example: stimulus id: b'background_stim'

                stim = 0
                stimonOff = 20

                if msg_parts[1] == b'Left':
                    stim = 4
                elif msg_parts[1] == b'Right':
                    stim = 3
                elif msg_parts[1] == b'forward':
                    stim = 9
                elif msg_parts[1] == b'backward':
                    stim = 13
                elif msg_parts[1] == b'background_stim':
                    stimonOff = 0
                    print('Stim off')
                elif msg_parts[1] == b'Left_Backward':
                    stim = 14
                elif msg_parts[1] == b'Right_Backward':
                    stim = 12
                elif msg_parts[1] == b'Left_Forward':
                    stim = 16
                elif msg_parts[1] == b'Right_Forward':
                    stim = 10

                self.links['stim_queue'].put({self.frame_num:[stim, stimonOff]}) #TODO: stimID needs to be numbered?
                self.stimmed.append([self.frame_num, stim])

            elif tag == b'frame':
                t0 = time.time()
                array = np.array(json.loads(msg_parts[1]))  # assuming the following message structure: 'tag: message'
                print('frame ', self.frame_num)
                # print('{}'.format(msg_parts[0])) # messsage length: {}. Element sum: {}; time to process: {}'.format(msg_parts[0], len(msg),
                                                                                            # array.sum(), time.time() - t0))
                # output example: b'frame ch0 10:02:01.115 AM 10/11/2019' messsage length: 1049637. Element sum: 48891125; time to process: 0.04192757606506348
                
                obj_id = self.client.put(array, 'acq_raw' + str(self.frame_num))
                self.q_out.put([{str(self.frame_num): obj_id}])

                self.saveArray.append(array)
                self.frametimes.append([self.frame_num, time.time()])

                self.frame_num += 1
                self.total_times.append(time.time() - t0)

            else:
                if len(msg) < 100:
                    print(msg)
                else:
                    print('msg length: {}'.format(len(msg)))

        except zmq.Again as e:
            pass #no messages available
        except Exception as e:
            print('error: {}'.format(e))

class ReplayAcquirer(FileAcquirer):
    def setup(self):
        super().__init__(*args, **kwargs)
        self.frame_num = 0

    def run(self):
        '''Triggered at Run
        '''
        self.total_times = []
        self.timestamp = []

        with RunManager(self.name, self.runAcquirer, self.setup, self.q_sig, self.q_comm) as rm:
            print(rm)

        print('Acquire broke, avg time per frame: ', np.mean(self.total_times))
        print('Acquire got through ', self.frame_num, ' frames')
        np.savetxt('timing/acquire_frame_time.txt', self.total_times)
        np.savetxt('timing/acquire_timestamp.txt', self.timestamp)

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


class TiffAcquirer(Actor):
    """
    Loops through a TIF file.

    """
    def __init__(self, *args, filename=None, framerate=30, **kwargs):
        super().__init__(*args, **kwargs)

        self.path = Path(filename)
        if not self.path.exists():
            raise ValueError(f'TIFF file {self.path} does not exist.')
        self.imgs = np.array(0)

        self.n_frame = 0
        self.fps = framerate

        self.t_per_frame = list()

    def setup(self):
        self.imgs = imread(self.path.as_posix())

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
