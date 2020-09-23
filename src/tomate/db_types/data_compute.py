"""Add convenience functions for various operations on data.

All functions were not thoroughly tested, use with caution.
"""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import Any, Callable, Dict, List, Tuple
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
        try:
            return self.apply_along_axes(np.nanmean, variable, dims,
                                         kwargs, **keys)
        except SqueezedAxesException as e:
            log.warning("You are averaging only on squeezed dimensions."
                        " Returning a view.")
            return e.var.view(keyring=e.keyring)

    def sum(self, variable: str, dims: List[str] = None,
            kwargs: Dict[str, Any] = None, **keys: KeyLike):
        """Compute sum on a given window.

        Arguments similar to :func:`mean`.
        Uses numpy.nansum.
        """
        try:
            return self.apply_along_axes(np.nansum, variable,
                                         dims, kwargs, **keys)
        except SqueezedAxesException as e:
            log.warning("You are summing only on squeezed dimensions."
                        " Returning a view.")
            return e.var.view(keyring=e.keyring)

    def std_dev(self, variable: str, dims: List[str] = None,
                kwargs: Dict[str, Any] = None,
                **keys: KeyLike):
        """Compute standard deviation on a given window.

        Arguments similar to :func:`mean`.
        Uses numpy.nanstd.
        """
        try:
            return self.apply_along_axes(np.nanstd, variable,
                                         dims, kwargs, **keys)
        except SqueezedAxesException as e:
            log.warning("You are computing standard deviation only on "
                        "squeezed dimensions.")
            return np.zeros(e.keyring.shape, dtype='f')

    def create_mean_variable(self, variable: str, dims: List[str],
                             name: str = None,
                             kwargs: Dict[str, Any] = None,
                             attributes: Dict[str, Any] = None):
        """Create a new variable that is the average of another.

        :param variable: Variable to average.
        :param dims: Dimensions to average along.
        :param name: [opt] New variable name, default to `variable_mean`.
        :param kwargs: [opt] Passed to numpy.nanmean.
        :param attributes: [opt] Attributes for the new variable.

        :raises IndexError: If there is no dimensions left after averaging.
            New variable cannot be a scalar.
        """
        var = self[variable]
        new_dims = [d for d in var.dims if d not in dims]
        if len(new_dims) == 0:
            raise IndexError("All dimensions were averaged.")

        if name is None:
            name = f'{variable}_mean'

        self.add_variable(name, dims=new_dims, var_class=type(var),
                          datatype=var.datatype, attrs=attributes)
        self[name].set_data(self.mean(variable, dims=dims, kwargs=kwargs))

        return self[name]

    def apply_along_axes(self, func: Callable, variable: str,
                         dims: str = None, kwargs: Dict[str, Any] = None,
                         **keys):
        """Apply a function on specific axes."""

        var = self[variable]
        var.check_loaded()

        if dims is None:
            dims = var.dims
        if kwargs is None:
            kwargs = {}

        keyring = Keyring.get_default(**keys)
        keyring.make_full(var.dims)
        keyring.limit(var.dims)
        keyring.sort_by(var.dims)
        keyring.make_total()
        keyring.set_shape(self.loaded.dims)

        order = keyring.get_non_zeros()
        axes = tuple([order.index(d) for d in dims if d in order])
        if len(axes) == 0:
            raise SqueezedAxesException(var, keyring)

        data = var.view(keyring=keyring)
        log.debug("Applying '%s' over axes %s", func.__name__, axes)
        result = func(data, axis=axes, **kwargs)
        return result


class SqueezedAxesException(Exception):
    """Computing on only squeezed axes."""
    def __init__(self, var, keyring):
        self.var = var
        self.keyring = keyring
