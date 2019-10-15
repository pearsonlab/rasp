import numpy as np
from analysis.analysis_utils import corr_frame_stim
from unittest import TestCase


class TestAnalysisUtils(TestCase):
    def test_corr_frame_stim(self):

        f = np.array([[0., 1],  # Time, frame
                      [1., 2],
                      [2., 3],
                      [3., 5],
                      [4., 6],
                      [50., 7]])
        s = np.array([[0.5, 99],  # Time, stim
                      [1, 96],
                      [3, 91],
                      [7, 42]])
        expected = np.array([[1., np.nan],  # t = 0  No stim info.
                             [2., 96.],  # t = 1  Stim newly updated.
                             [3., 96.],  # t = 2  Use data at t = 1
                             [5., 91.],  # t = 3  Stim newly updated.
                             [6., 91.],  # t = 4  Use data at t = 6
                             [7., 42.]])  # t = 50 Use data at t = 7
        self.assert_(np.allclose(corr_frame_stim(f, s), expected, equal_nan=True))
