"""Add convenience functions for various operations on data."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import Any, Callable, Dict, List, Union
import logging

import numpy as np

from tomate.custom_types import Array, KeyLike
from tomate.data_base import DataBase
from tomate.keys.keyring import Keyring
from tomate.variables import VariableMasked

log = logging.getLogger(__name__)


class DataCompute(DataBase):
    """Data class with added functionalities for various computations.

    See :class:`DataBase` for more information.
    """

    def histogram(self, variable, bins=None, bounds=None,
                  density=False, **keys):
        data = self.view(variable, **keys).compressed()
        return np.histogram(data, bins=bins, range=bounds,
                            density=density)

    def gradient(self, variable: str,
                 coords: List[str], fill=None) -> Array:
        """Compute a n-dimensional gradient.

        :param coords: Coordinates to compute the gradient along.
        """
        var = self[variable]
        var.check_loaded()
        axis = [var.dims.index(c) for c in coords]
        values = [self.loaded.coords[c][:] for c in coords]

        if issubclass(type(var), VariableMasked):
            data = var.filled(fill)
        else:
            data = var[:]
        grad = np.gradient(data, *values, axis=axis)
        return grad

    def gradient_magn(self, variable: str, coords: List[str] = None,
                      fill=None) -> Array:
        """Compute the gradient magnitude.

        See also
        --------
        gradient: Compute the gradient.
        """
        grad = self.gradient(variable, coords, fill)
        magn = np.linalg.norm(grad, axis=0)

        if issubclass(type(self[variable]), VariableMasked):
            mask = self[variable].mask.copy()
            magn = np.ma.array(magn, mask=mask)
        return magn

    def derivative(self, variable: str, coord: str) -> Array:
        """Compute derivative along a coordinate.

        Other coordinates are looped over.
        """
        der = self.gradient_nd(variable, [coord])
        return der

    def mean(self, variable: str, dims: List[str] = None,
             kwargs: Dict[str, Any] = None,
             **keys: KeyLike) -> Array:
        """Compute average on a given window.


        :param dims: Coordinates to compute the mean along.
        :param kwargs: [opt] Argument passed to numpy.nanmean
        :param keys: Part of the data to consider for averaging (by index).

        Examples
        --------
        >>> avg = db.mean('SST', ['lat', 'lon'], lat=slice(0, 50))

        Compute the average SST on the 50 first indices of latitude,
        and all longitude. If the data is indexed on [time, lat, lon]
        `avg` is a one dimensional array.
        """
        var = self[variable]
        var.check_loaded()

        if dims is None:
            dims = var.dims
        if kwargs is None:
            kwargs = {}

        keyring = Keyring.get_default(**keys)
        keyring.make_full(var.dims)
        keyring.make_total()
        keyring.sort_by(var.dims)
        order = keyring.get_non_zeros()
        axes = tuple([order.index(d) for d in dims if d in order])
        if len(axes) == 0:
            log.warning("You are averaging only on squeezed dimensions."
                        " Returning a view.")
            return var.view(keyring=keyring)

        mean = np.nanmean(var.view(keyring=keyring), axes, **kwargs)
        return mean

    def std_dev(self, variable: str, dims: str = None,
                kwargs: Dict[str, Any] = None,
                **keys: KeyLike):
        """Compute standard deviation on a given window."""
        var = self[variable]
        var.check_loaded()

        if dims is None:
            dims = var.dims
        if kwargs is None:
            kwargs = {}

        keyring = Keyring.get_default(**keys)
        keyring.make_full(var.dims)
        keyring.make_total()
        keyring.sort_by(var.dims)
        order = keyring.get_non_zeros()
        axes = tuple([order.index(d) for d in dims if d in order])
        if len(axes) == 0:
            log.warning("You are computing only on squeezed dimensions."
                        " Returning zeros.")
            data = var.view(keyring=keyring)
            data[:] = 0
            return data

        std = np.nanstd(var.view(keyring=keyring), axes, **kwargs)
        return std

    def linear_combination(self):
        """Compute linear combination between variables."""
        raise NotImplementedError


def do_stack(func: Callable, ndim: int,
             array: Array, *args: Any,
             axes: List[int] = None,
             output=None, **kwargs: Any):
    """Apply func over certain axes of array. Loop over remaining axes.

    :param func: Function which takes a slice of array.
        Dimension of slice is dictated by `ndim`.
    :param ndim: The number of dimensions func works on. The remaining dimension
        in input array will be treated as stacked and looped over.
    :param axes: Axes that func should work over, default is the last ndim axes.
    :param output: Result passed to output. default to np.zeros.
    """
    if axes is None:
        axes = list(range(-ndim, 0))
    lastaxes = list(range(-ndim, 0))

    # Swap axes to the end
    for i in range(ndim):
        array = np.swapaxes(array, axes[i], lastaxes[i])

    # Save shape
    stackshape = array.shape[:-ndim]

    if output is None:
        output = np.zeros(array.shape)

    # Place all stack into one dimension
    array = np.reshape(array, (-1, *array.shape[-ndim:]))
    output = np.reshape(output, (-1, *output.shape[-ndim:]))

    for i in range(array.shape[0]):
        output[i] = func(array[i], *args, **kwargs)

    array = np.reshape(array, (*stackshape, *array.shape[-ndim:]))
    output = np.reshape(output, (*stackshape, *output.shape[-ndim:]))

    # Reswap axes
    for i in range(ndim):
        array = np.swapaxes(array, axes[i], lastaxes[i])
        output = np.swapaxes(output, axes[i], lastaxes[i])

    return output
