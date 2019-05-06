from process.process import Processor

import logging; logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class BatchProcessor(Processor):
    ''' Class used for processing frames in batch mode
        Rather than run on 1 frame at a time, each run
        waits for a set number of frames (window).
    '''

    