import logging
import os
import time
from concurrent.futures import Future, ProcessPoolExecutor
from queue import Empty

import numpy as np
import tifffile
from colorama import Fore
from suite2p import run_s2p

from nexus.module import RunManager
from nexus.store import ObjectNotFoundError
from process.process import Processor

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class BatchProcessor(Processor):
    """
    Process frames in batches using suite2p.
    Analysis is called every {buffer_size} frames.

    """

    def __init__(self, *args, buffer_size=200, path='../output', max_workers=2):
        """
        :param buffer_size: Size of frame batches.
        :param path: Path to saved TIFF files.
        :param max_workers: Maximum number of suite2p processes to be running concurrently.
        """
        super().__init__(*args)

        self.buffer_size = buffer_size
        self.path = path

        self.frame_buffer: np.ndarray = None
        self.frame_number = 0

        self.tiff_name = list()
        self.futures = list()

        self.t_per_frame = list()
        self.t_per_put = list()
        self.pool = ProcessPoolExecutor(max_workers=max_workers)

    def setup(self):
        pass

    def run(self):
        with RunManager(self.name, self.runner, self.setup, self.q_sig, self.q_comm) as rm:
            logger.info(rm)

    def runner(self):
        """
        Gets raw frames from store, put them into {self.frame_buffer}.
        Every {self.buffer_size}, calls {self.call_suite}.

        """

        try:
            obj_id = self.q_in.get(timeout=1e-3)  # List
            frame = self.client.getID(obj_id[0][str(self.frame_number)])  # Expects np.ndarray
        except Empty:
            pass

        except KeyError as e:
            logger.error('Processor: Key error... {0}'.format(e))
        except ObjectNotFoundError:
            logger.error('Unavailable from store, dropping frame_number.')

        else:
            if self.frame_number % self.buffer_size == 0:
                self.frame_buffer = np.zeros((self.buffer_size, frame.shape[0], frame.shape[1]), dtype=frame.dtype)

            t = time.time()
            self.frame_buffer[self.frame_number % self.buffer_size] = frame

            # Save and call
            if self.frame_number % self.buffer_size == self.buffer_size - 1:
                print(Fore.GREEN + f'Calling suite!' + Fore.RESET)
                self.call_suite()

            self.frame_number += 1
            self.t_per_frame.append([time.time(), time.time() - t])

    def call_suite(self):
        """
        Save {self.frame_buffer} into a TIFF file.
        Launches suite2p into a new process.

        """
        self.tiff_name.append(
            f'{time.strftime("%Y-%m-%d-%H%M%S")}_frame{self.frame_number - self.buffer_size + 1}to{self.frame_number}'
        )

        # Need to create a new folder for each file to prevent suite2p from overwriting old files.
        path = f'{self.path}/{self.tiff_name[-1]}/'
        if not os.path.exists(path):
            os.makedirs(path)

        tifffile.imsave(f'{path}/{self.tiff_name[-1]}.tiff', self.frame_buffer)
        ops = run_s2p.default_ops()
        db = {'data_path': [path],
              'tiff_list': [f'{self.tiff_name[-1]}.tiff']}

        self.futures.append(self.pool.submit(run_s2p.run_s2p, ops=ops, db=db))
        self.futures[-1].add_done_callback(self.putEstimates)

    def putEstimates(self, future: Future):
        """
        Callback from suite2p.

        """
        print(future.result())
