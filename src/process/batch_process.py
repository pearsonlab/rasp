from process.process import Processor

import logging; logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class BatchProcessor(Processor):
    ''' Class used for processing frames in batch mode
        Rather than run on 1 frame at a time, each run
        waits for a set number of frames (window).
    '''

    def setup(self, window=100):
        ''' Define batch windows size; default is 100 frames
        '''
        self.window = window
        self.frame_number = 0
        self.frames = []

    def run(self):
        self.flag = False
        while True:
            if self.flag: #if we have received run signal
                try: 
                    self.runBatching()
                    if self.done:
                        logger.info('Done running Batch Process')
                        return
                except Exception as e:
                    logger.exception('What happened: {0}'.format(e))
                    break  
            try: 
                signal = self.q_sig.get(timeout=1)
                if signal == Spike.run(): 
                    self.flag = True
                    logger.warning('Received run signal, begin running process')
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

    def runBatching(self):
        ''' Accumulate frames until window reached, then process
        '''
        try:
            frame = self.q_in.get()
        except CannotGetObjectError:
            logger.error('No frames')
        
        if frame is not None:
            try:
                frames.append(self.client.getID(frame[0][str(self.frame_number)]))
                if self.frame_number % self.window == 0:
                    self.processBatch()
                self.frame_number += 1
            except ObjectNotFoundError:
                logger.error('Frame unavailable from store, droppping')
                self.frame_number += 1
            except KeyError as e:
                logger.error('Key error... {0}'.format(e))
        else:
            logger.error('Done with all available frames: {0}'.format(self.frame_number))
            self.q_comm.put(None)
            self.done = True

    def processBatch(self):
        ''' Process the set of frames
        '''
        pass

    def putEstimates(self):
        ''' Put output of processing into DS
        '''
        pass