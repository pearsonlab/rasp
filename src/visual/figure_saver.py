import time
from contextlib import contextmanager
from pathlib import Path

import imageio
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

sns.set()
DPI = 200


class FigureSaver:
    """
    Class to save plots/images from the improv frontend.
    Track saved figures to generate GIFs.

    """

    def __init__(self, path_save='/results/improv'):

        self.path_save = Path(path_save)
        self.path_save.mkdir(parents=True, exist_ok=True)
        self.types = ['activity', 'model']

        self.files = {name: list() for name in self.types}

    def save_activity(self, Cx, C, Cpop, raw, color, name=None):
        """ Save raw/processed images and neuron/population activity plot. """

        if name is None:
            name = f'imgs_{time.time()}.png'

        print(f'Saved as {name}.')

        with self._gen_fig(n=(2, 2), dpi=DPI, save=name) as axs:
            axs[0].imshow(raw, cmap='gray')
            axs[0].set_axis_off()
            axs[0].set_title('Raw Image', fontsize=14, loc='left', pad=9)

            axs[1].imshow(color)
            axs[1].set_axis_off()
            axs[1].set_title('Processed Image', fontsize=14, loc='left', pad=9)

            axs[2].plot(Cx, Cpop)
            axs[2].set_xlabel('Frame')
            axs[2].set_ylabel('Population Activity')
            axs[2].set_title('Population Activity', fontsize=14, loc='left', pad=9)

            axs[3].plot(Cx, C)
            axs[3].set_xlabel('Frame')
            axs[3].set_ylabel('Neuron Activity')
            axs[3].set_title('Circled Neuron Activity', fontsize=14, loc='left', pad=9)

        self.files['activity'].append(self.path_save / name)

    def save_model(self, LL, weights, name=None):
        """ Save LL and weights matrix. """

        if name is None:
            name = f'model_{time.time()}.png'

        print(f'Saved as {name}.')

        with self._gen_fig(n=(1, 2), dpi=DPI, save=name) as axs:
            axs[0].plot(LL)
            axs[0].set_xlabel('Frame')
            axs[0].set_ylabel('log-likelihood')
            axs[0].set_title('Log-likelihood', fontsize=14, loc='left', pad=9)

            axs[1].imshow(weights, cmap='viridis')
            axs[1].grid('off')

        self.files['model'].append(self.path_save / name)

    def gen_gif(self):
        """ Combine all saved images of each type into a GIF file. """
        for name, fs in self.files.items():
            images = [imageio.imread(f) for f in fs]
            imageio.mimsave((self.path_save / f'{name}.gif').as_posix(), images, duration=0.5)

    @contextmanager
    def _gen_fig(self, size=(5, 4), dpi=100, n=(1, 1), save=None):
        """
        Helper context manager to streamline plotting.
        {n} is the number of plots in [rows, columns] format.
        Yields AxesSubplot when n == (1, 1) else an np.ndarray of AxesSubplot with shape [n].

        """
        figsize = (size[0] * n[1], size[1] * n[0])
        fig, ax = plt.subplots(nrows=n[0], ncols=n[1], figsize=figsize, dpi=dpi)
        if max(n) > 1:
            ax = np.reshape(ax, n[0] * n[1])
        yield ax

        plt.tight_layout()
        if save is not None:
            plt.savefig(self.path_save / save)
        plt.close(fig)
