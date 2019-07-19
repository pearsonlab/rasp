import logging
import time
from queue import Empty

import colorama
import numpy as np

from nexus.module import RunManager
from nexus.store import ObjectNotFoundError
from .analysis import Analysis

"""Need to run this, otherwise https://pyjulia.readthedocs.io/en/latest/troubleshooting.html#your-python-interpreter-is-statically-linked-to-libpython"""
from julia.api import Julia
print(f'Loading Julia. This will take ~30 s.')
j = Julia(compiled_modules=False)
from julia import Main

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class JuliaAnalysis(Analysis):
    """
    Class to run analyses in Julia.

    This class puts in q_out the average frame_number intensity every 10 frames.

    """

    def __init__(self, *args):
        super().__init__(*args)
        self.run_every_n_frames = 10

        self.frame_number = 0
        self.frame_buffer = list()
        self.result_ex = None  # np.ndarray

        self.t_per_frame = list()
        self.t_per_put = list()

    def setup(self, param_file=None):
        # Import Julia libs
        Main.eval("""import Statistics: mean
                     result = zeros(10)""")

    def run(self):
        with RunManager(self.name, self.runner, self.setup, self.q_sig, self.q_comm) as rm:
            logger.info(rm)

        print(f'JuliaAnalysis broke, avg time per frame_number: {np.mean(self.t_per_frame)}.')
        print(f'JuliaAnalysis broke, avg time per put analysis: {np.mean(self.t_per_put)}.')
        print(f'JuliaAnalysis got through {self.frame_number} frames.')

    def runner(self):
        t = time.time()

        try:
            obj_id = self.q_in.get(timeout=0.0001)  # List
            self.frame_buffer.append(self.client.getID(obj_id[0][str(self.frame_number)]))  # Expected np.ndarray

        except Empty:
            pass
        except KeyError as e:
            logger.error('Processor: Key error... {0}'.format(e))
        except ObjectNotFoundError:
            logger.error('Unavailable from store, dropping frame_number.')

        else:
            self.frame_number += 1
            if len(self.frame_buffer) > self.run_every_n_frames:
                self.run_julia_analyses()

        self.t_per_frame.append([time.time(), time.time() - t])

    def run_julia_analyses(self):
        Main.x = np.array(self.frame_buffer)
        Main.eval("""for i in 1:10
                        result[i] = mean(x[i, :, :])
                     end""")
        self.result_ex = Main.result
        print(f'{colorama.Fore.GREEN} Julia: mean intensity of frame {self.frame_number} is {self.result_ex[-1]}')
        self.frame_buffer = list()

    def export(self):
        t = time.time()
        obj_ids = [self.client.put(self.result_ex, f'resultJulia{self.frame_number}')]

        # Automatic eneration of variables to export.
        # export_list = [key for key, value in self.__dict__.items() if key.endswith('_ex')]
        # obj_ids = list()
        # for var in export_list:
        #     obj_ids.append(self.client.put(eval(f'self.{var}'), f'{var[:-3]}{curr_frame}'))

        self.q_out.put(obj_ids)
        self.t_per_put.append(time.time() - t)
