"""Add convenience functions for various operations on data.

All functions were not thoroughly tested, use with caution.
"""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import Any, Dict, List, Tuple
import logging

import numpy as np

from tomate.custom_types import Array, KeyLike
from tomate.data_base import DataBase
from tomate.keys.keyring import Keyring
from tomate.var_types.variable_masked import VariableMasked

log = logging.getLogger(__name__)


class DataCompute(DataBase):
    """Data class with added functionalities for various computations.

    All functions were not thoroughly tested, use with caution.

    See :class:`DataBase` for more information.
    """

    def histogram(self, variable, bins=None, bounds=None,
                  density=False, **keys) -> Tuple[np.ndarray]:
        """Compute histogram."""
        data = self.view(variable, **keys).compressed()
        return np.histogram(data, bins=bins, range=bounds,
                            density=density)

    def gradient(self, variable: str,
                 coords: List[str], fill=None) -> Array:
        """Compute a n-dimensional gradient.

        :param coords: Coordinates to compute the gradient along.
        :param fill: [opt] Value to fill masked data.
        """
        var = self[variable]
        var.check_loaded()
        axis = [var.dims.index(c) for c in coords]
        values = [self.loaded.coords[c][:] for c in coords]

        if isinstance(var, VariableMasked):
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

        if isinstance(self[variable], VariableMasked):
            mask = self[variable].mask.copy()
            magn = np.ma.array(magn, mask=mask)
        return magn

    def derivative(self, variable: str, coord: str) -> Array:
        """Compute derivative along a coordinate.

        Other coordinates are looped over.
        """
        der = self.gradient(variable, [coord])
        return der

    def mean(self, variable: str, dims: List[str] = None,
             kwargs: Dict[str, Any] = None,
             **keys: KeyLike) -> Array:
        """Compute average on a given window.

        :param dims: Coordinates to compute the mean along.
        :param kwargs: [opt] Arguments passed to numpy.nanmean
        :param keys: Part of the data to select.

        Examples
        --------
        >>> avg = db.mean('SST', ['lat', 'lon'], lat=slice(0, 50))

        Compute the average SST on the 50 first indices of latitude,
        and all longitude. If the data is indexed on [time, lat, lon]
        `avg` is a one dimensional array (for time dimension).
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

        data = var.view(keyring=keyring)
        log.debug("Averaging over axes %s", axes)
        mean = np.nanmean(data, axes, **kwargs)
        return mean

    def std_dev(self, variable: str, dims: str = None,
                kwargs: Dict[str, Any] = None,
                **keys: KeyLike):
        """Compute standard deviation on a given window.

        Arguments similar to :func:`mean`.
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
            log.warning("You are computing only on squeezed dimensions.")

        data = var.view(keyring=keyring)
        log.debug("Computing standard deviation over axes %s", axes)
        std = np.nanstd(data, axes, **kwargs)
        return std
