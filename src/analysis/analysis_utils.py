import numpy as np


def corr_frame_stim(t_frame, t_stim):
    """
    Return [frame number, stimulus] pairs given time data of frame number and stimulus number.

    Frame numbers are associated to the last stimulus that happened before the frame.
    If there is no stimulus prior to the frame, np.nan is used instead.

    :param t_frame: [Time, Frame number] in each row.
    :param t_stim: [Time, Stim number]
    :type t_frame: np.ndarray
    :type t_stim: np.ndarray
    :return: [Frame number, stim]
    :rtype: np.ndarray
    """

    for arr in [t_frame, t_stim]:
        assert len(arr.shape) == 2
        assert not (np.isnan(np.sum(arr)) and np.isinf(np.sum(arr)))

    t_frame = sort_np_wrt_col(t_frame, 0)
    t_stim = sort_np_wrt_col(t_stim, 0)
    assert np.all(t_frame[:-1, 1] < t_frame[1:, 1])  # Frame number must increase monotonically.

    out = np.flip(t_frame, axis=1).copy()
    for i in range(t_frame.shape[0]):
        idx = np.searchsorted(t_stim[:, 0], t_frame[i, 0], side='right') - 1
        out[i, 1] = t_stim[idx, 1] if idx > -1 else np.nan
    return out


def sort_np_wrt_col(arr, col: int):
    """
    Sort np.ndarray using {col} as the index.

    >>> sort_np_wrt_col(np.array([[1, 2], [3, 0]]), 1)
    array([[3, 0],
       [1, 2]])

    :param arr: Input (expecting 2D array).
    :param col: Column to be used as index.
    :rtype arr: np.ndarray
    :rtype col: int
    :return: Sorted np.ndarray
    :rtype: np.ndarray
    """
    if not np.all(arr[:-1, col] <= arr[1:, col]):
        return arr[arr[:, col].argsort()]
    else:
        return arr
