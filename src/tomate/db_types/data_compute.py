"""Add convenience functions for various operations on data."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import Any, Callable, Dict, List
import logging

import numpy as np

from tomate.custom_types import Array, KeyLike
from tomate.data_base import DataBase
from tomate.keys.keyring import Keyring

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
        self.check_loaded()
        axis = [self.coords.index(c) for c in coords]
        values = [self.coords[c][:] for c in coords]

        if 'DataMasked' in self.bases:
            data = self.filled(fill, variables=variable)
        else:
            data = self[variable]
        grad = np.gradient(data, *values, axis=axis)
        return grad

    def gradient_magn(self, variable: str,
                      coords: List[str] = None) -> Array:
        """Compute the gradient magnitude.

        See also
        --------
        gradient: Compute the gradient.
        """
        grad = self.gradient(variable, coords)
        magn = np.linalg.norm(grad, axis=0)

        if np.ma.isMaskedArray(self.data):
            mask = self[variable].mask.copy()
            magn = np.ma.array(magn, mask=mask)
        return magn

    def derivative(self, variable: str, coord: str) -> Array:
        """Compute derivative along a coordinate.

        Other coordinates are looped over.
        """
        der = self.gradient_nd(variable, [coord])
        return der

    def apply_on_subpart(self, func: Callable,
                         args: List[Any] = None,
                         kwargs: Dict[str, Any] = None,
                         keyring: Keyring = None,
                         **keys: KeyLike):
        """Apply function on data subset.
        """
        self.check_loaded()

        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}

        data = self.view(keyring=keyring, **keys)
        res = func(data, *args, **kwargs)
        return res

    def mean(self, dims: List[str] = None,
             kwargs: Dict[str, Any] = None,
             **keys: KeyLike) -> Array:
        """Compute average on a given window.


        :param dims: Coordinates to compute the mean along.
        :param kwargs: [opt] Argument passed to numpy.nanmean
        :param keys: Part of the data to consider for averaging (by index).

        Examples
        --------
        >>> avg = db.mean(['lat', 'lon'], var='SST', lat=slice(0, 50))

        Compute the average SST on the 50 first indices of latitude,
        and all longitude. If the data is indexed on [time, lat, lon]
        `avg` is a one dimensional array.
        """
        if dims is None:
            dims = self.dims

        keyring = Keyring.get_default(**keys)
        keyring.make_full(self.dims)
        keyring.make_total()
        keyring.sort_by(self.dims)
        order = keyring.get_non_zeros()
        axes = tuple([order.index(d) for d in dims if d in order])
        if len(axes) == 0:
            log.warning("You are averaging only on squeezed dimensions."
                        " Returning a view.")
            return self.view(keyring=keyring)

        if kwargs is None:
            kwargs = {}

        mean = self.apply_on_subpart(np.nanmean, args=[axes],
                                     kwargs=kwargs, keyring=keyring)
        return mean

    def std_dev(self, dims: str = None,
                kwargs: Dict[str, Any] = None,
                **keys: KeyLike):
        """Compute standard deviation on a given window."""
        if dims is None:
            dims = self.dims_name

        keyring = Keyring.get_default(**keys)
        keyring.make_full(self.dims)
        keyring.make_total()
        keyring.sort_by(self.dims)
        order = keyring.get_non_zeros()
        axes = tuple([order.index(d) for d in dims if d in order])
        if len(axes) == 0:
            log.warning("You are computing only on squeezed dimensions."
                        " Returning zeros.")
            data = self.view(keyring=keyring)
            data[:] = 0
            return data

        if kwargs is None:
            kwargs = {}

        mean = self.apply_on_subpart(np.nanstd, args=[axes], kwargs=kwargs, **keys)
        return mean

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
