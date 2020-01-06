"""Manages some aspects of masked data."""

import numpy as np
import scipy.ndimage as ndimage

from data_loader.data_compute import do_stack



def get_circle_kernel(n):
    """Return circular kernel for convolution of size nxn."""
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
    N = 2*n_neighbors + 1
    kernel = get_circle_kernel(N)

    mask = do_stack(ndimage.convolve, 2, 1.*mask, kernel, axes) > 0

    return mask
