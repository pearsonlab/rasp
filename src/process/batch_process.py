import logging
import time
from pathlib import Path
from queue import Empty
import numpy as np
import tifffile
from caiman.utils.visualization import get_contours
from scipy.sparse import csc_matrix, hstack
from suite2p import run_s2p
from nexus.actor import Actor, RunManager
from nexus.store import ObjectNotFoundError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Suite2pProcessor(Actor):
    ''' Process frames in batches using suite2p.
        Analysis is called every {buffer_size} frames.
        Designed for output to ModelAnalysis.
    '''

    def __init__(self, *args, buffer_size=200, path='output', **kwargs):
        ''' buffer_size: Size of frame batches.
            path: Path to saved TIFF files.
        '''
        
        super().__init__(*args)

        self.buffer_size = buffer_size
        self.path = Path(path)
        self.path.mkdir(exist_ok=True)

        self.frame_buffer: np.ndarray = None
        self.frame_number = 0

        self.tiff_name = list()
        self.futures = list()

        self.t_per_frame = list()
        self.t_per_put = list()

        self.A = None
        self.S = None
        self.first = True

        # suite2p settings.
        self.suite_ops = run_s2p.default_ops()
        mod = {'tau': 0.7,
               'fs': 2,
               'smooth_sigma_time': 1,
               'spatial_scale': 1,
               'min_neuropil_pixels': 100,
               'threshold_scaling': 6,
               'do_registration': False,  # TODO Registration does not work with improv.
               }

        for k, v in mod.items():
            self.suite_ops[k] = v

    def setup(self):
        pass

    def run(self):
        with RunManager(self.name, self.runner, self.setup, self.q_sig, self.q_comm) as rm:
            logger.info(rm)

    def runner(self):
        ''' Get raw frames from store, put them into {self.frame_buffer}.
            Every {self.buffer_size}, call {self.call_suite}.
        '''

        try:
            obj_id = self.q_in.get(timeout=1e-3)  # List
            frame = self.client.getID(obj_id[0][str(self.frame_number)])  # Expects np.ndarray
        except Empty:
            pass

        except KeyError as e:
            logger.error('Processor: Key error... {0}'.format(e))
        except ObjectNotFoundError:
            logger.error('Unavailable from store, dropping frame_number {}.'.format(self.frame_number))

        else:
            # Put frame into buffer. Regenerate when full.
            if self.frame_number % self.buffer_size == 0:
                self.frame_buffer = np.zeros((self.buffer_size, frame.shape[0], frame.shape[1]), dtype=frame.dtype)

            t = time.time()
            self.frame_buffer[self.frame_number % self.buffer_size] = frame

            # Save buffer as TIF and send to suite2p.
            if self.frame_number % self.buffer_size == self.buffer_size - 1:
                print('Calling suite2p!')
                self.run_suite()

            self.frame_number += 1
            self.t_per_frame.append([time.time(), time.time() - t])

    def run_suite(self):
        ''' Save {self.frame_buffer} into a TIFF file.
            Call suite2p using the said TIFF file.
            Put processed/merged results into store.
        '''

        t0 = time.time()

        self.tiff_name.append(
            f'{time.strftime("%Y-%m-%d-%H%M%S")}_frame{self.frame_number - self.buffer_size + 1}to{self.frame_number}'
        )

        # Need to create a new folder for each file to prevent suite2p from overwriting old files.
        path = self.path / self.tiff_name[-1]
        path.mkdir(exist_ok=True)

        tifffile.imsave(path / f'{self.tiff_name[-1]}.tif', self.frame_buffer)

        db = {
            'data_path': [path.as_posix()],
            'tiff_list': [f'{self.tiff_name[-1]}.tif']
        }

        run_s2p.run_s2p(ops=self.suite_ops, db=db)

        to_put = self.process_suite_results(path)
        self.put_estimates(*to_put)
        self.t_per_put.append(time.time() - t0)
        logger.info('suite2p: processed up to frame {}.'.format(self.frame_number))

    def process_suite_results(self, path: Path):
        ''' Convert suite2p result into the output format of CaimanProcessor.
            Initializes class data when run for the first time. Otherwise, merge new results.
            Frame number is frame number when suite2p is called.

            path: Path to suite2p result folder.
            Returns list of [coords, mean_image, S].
        '''

        path = path / 'suite2p' / 'plane0'

        # Want coords (encoded in A), image, S
        # Specifications:
        # estimates.A: Set of spatial components. Saved as a sparse column format matrix with dimensions (# of pixels X # of components). Each column corresponds to a spatial component.
        # estimates.S: Deconvolved neural activity (spikes) for each component. Saved as a numpy array with dimensions (# of background components X # of timesteps). Each row corresponds to the deconvolved neural activity for the corresponding component.

        S = np.load(f'{path}/spks.npy')
        stat = np.load(f'{path}/stat.npy', allow_pickle=True)
        ops: dict = np.load(f'{path}/ops.npy', allow_pickle=True).item()  # Load settings.

        if self.first:
            self.dim_img = np.array((ops['Lx'], ops['Ly']))
            self.batch_size = ops['nframes']

            A = csc_matrix((self.dim_img[0] * self.dim_img[1], len(stat)), dtype=np.float32)  # pxs x n_neurons
            for i, cell in enumerate(stat):
                # Color cell loc
                t = np.zeros(self.dim_img, dtype=np.bool)
                t[cell['xpix'], cell['ypix']] = 1
                A[:, i] = csc_matrix(t.reshape((self.dim_img[0] * self.dim_img[1], 1)), dtype=np.float32)

            self.A = A
            self.S = S
            self.median_xy = np.array([s['med'] for i, s in enumerate(stat)])
            self.first = False

        else:
            self.merge_suite_results(S, stat)

        img_mean = ops['meanImg'] / np.max(ops['meanImg']) * 256

        return get_contours(self.A, self.dim_img[::-1]), img_mean, self.S

    def merge_suite_results(self, new_S, new_stat):
        ''' Merge results from different batches of suite2p.

            If L1-distance of median (x, y) is less than 4, combine spike data. Else, create new neuron.
            If old neuron disappears, pad with 0.
        '''

        # Median, padded with idx and old/new flag.
        med = np.array([[*xy, i, 0] for i, xy in enumerate(self.median_xy)])
        new_med = np.array([[*s['med'], i, 1] for i, s in enumerate(new_stat)])

        # Find matching neurons. Sum difference row-wise of x and y.
        list_neu = np.concatenate((med, new_med), axis=0)
        list_neu = list_neu[list_neu[:, 0].argsort()]  # Sort by x-coord.

        diff = np.hstack((np.ediff1d(list_neu[:, 0])[:, np.newaxis], np.ediff1d(list_neu[:, 1])[:, np.newaxis]))
        diff = np.sum(np.abs(diff), axis=1)
        match = np.argwhere(diff < 4)  # L1-distance.

        cursor_new = self.S.shape[0]
        n_to_add = len(new_med) - len(match)

        # Add space to current A and S.
        A_toconcat = csc_matrix(np.zeros((self.A.shape[0], n_to_add), dtype=self.A.dtype))
        self.A = hstack([self.A, A_toconcat])
        self.S = np.vstack((self.S, np.zeros((n_to_add, self.S.shape[1]), dtype=self.S.dtype)))
        self.S = np.hstack((self.S, np.zeros((self.S.shape[0], self.batch_size), dtype=self.S.dtype)))
        self.median_xy = np.vstack((self.median_xy, np.zeros((n_to_add, 2))))

        # Update current A and S.
        skip = False
        for i in range(list_neu.shape[0]):
            if skip:
                skip = False
                continue

            if i in match:  # Update only S.
                # Find index
                idxs = np.zeros(2, dtype=np.int)
                idxs[int(list_neu[i, 3])] = list_neu[i, 2]
                idxs[int(list_neu[i + 1, 3])] = list_neu[i + 1, 2]

                self.S[idxs[0], -self.batch_size:] = new_S[idxs[1], :]

                # Skip next idx.
                skip = True

            elif list_neu[i, 3]:  # Unique in new, update med, A and S.
                idx = int(list_neu[i, 2])
                t = np.zeros(self.dim_img, dtype=np.bool)
                t[new_stat[idx]['xpix'], new_stat[idx]['ypix']] = 1
                self.A[:, cursor_new] = csc_matrix(t.reshape((self.dim_img[0] * self.dim_img[1], 1)),
                                                   dtype=np.float32)

                self.S[cursor_new, -self.batch_size:] = new_S[idx, :]
                self.median_xy[cursor_new, :] = list_neu[i, :2]
                cursor_new += 1

            else:  # Unique in old, do nothing.
                pass

    def put_estimates(self, coords, img_mean, S):
        ''' Put relevant analyses results into the data store
            for later classes (e.g. ModelAnalysis) to access
        '''
        ids = []
        ids.append(self.client.put(coords, 'coords'+str(self.frame_number+1)))
        ids.append(self.client.put(img_mean, 'proc_image'+str(self.frame_number+1)))
        ids.append(self.client.put(S, 'S'+str(self.frame_number+1)))
        ids.append(self.frame_number+1)
        self.q_out.put(ids)