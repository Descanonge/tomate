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

from tomate.util.do_stack import do_stack


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
