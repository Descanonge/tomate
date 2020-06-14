"""Manages some aspects of masked data."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import numpy as np

try:
    import scipy.ndimage as ndimage
except ImportError:
    _has_scipy = False
else:
    _has_scipy = True

from tomate.db_types.data_compute import do_stack


def get_circle_kernel(n):
    """Return circular kernel for convolution of size nxn.

    Parameters
    ----------
    n: int
        Diameter of kernel.

    Returns
    -------
    Array
        Shape (n, n)
    """
    kernel = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            kernel[i, j] = (i-(n-1)/2)**2 + (j-(n-1)/2)**2 <= (n/2)**2

    return kernel


def enlarge_mask(mask, n_neighbors, axes=None):
    """Enlarge a stack of boolean mask by `n_neighbors`.

    Parameters
    ----------
    mask: Array
    n_neighbors: int
    axes: List[int]
        Position of the two horizontal dimensions,
        other axes will be looped over.
    """
    if not _has_scipy:
        raise ImportError("scipy package necessary to use enlarge_mask.")

    N = 2*n_neighbors + 1
    kernel = get_circle_kernel(N)

    mask = do_stack(ndimage.convolve, 2, 1.*mask, kernel, axes) > 0

    return mask


def fill_edge(data, axes=None):
    """Fill masked by value of closest pixel.

    Parameters
    ----------
    data: Array
    axes: List[int]
        Axes to work on.
        If None, the last two axes are used.
    """
    if not _has_scipy:
        raise ImportError("scipy package necessary to use fill_edge.")

    mask = data.mask
    small_mask = ~enlarge_mask(~mask, 1, axes=axes)
    to_fill_mask = small_mask * mask

    kernel = np.array([[0, 1, 0],
                       [1, 0, 1],
                       [0, 1, 0]])
    to_fill = do_stack(ndimage.convolve, 2, data.filled(0), kernel, axes)
    data.data[to_fill_mask] = to_fill
    return np.ma.array(data, mask=small_mask)
