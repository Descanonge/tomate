"""Variable class for masked data."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import List, Union
import logging

import numpy as np

from tomate.custom_types import Array, KeyLike
from tomate.accessor import Accessor
from tomate.variable_base import Variable


log = logging.getLogger(__name__)


class AccessorMask(Accessor):
    """Accessor for masked numpy array."""

    @staticmethod
    def allocate(shape: List[int], datatype=None) -> Array:
        array = np.ma.zeros(shape, dtype=datatype)
        array.mask = np.ma.make_mask_none(shape)
        return array

    @staticmethod
    def concatenate(arrays: List[Array], axis: int = 0, out=None) -> Array:
        """Concatenate arrays.

        :param axis: [opt] The axis along which the arrays will be joined.
            If None, the arrays are flattened.
        """
        if out is not None:
            raise TypeError("np.ma.concatenate does not support 'out' argument")
        return np.ma.concatenate(arrays, axis=axis)

    @staticmethod
    def stack(arrays: List[Array],
              axis: int = 0,
              out: Array = None) -> Array:
        """Stack arrays along a new axis.

        :param arrays: Arrays to stack.
        :param axis: The axis along which the arrays will be joined.
        :param out: Array to place the result in.

        See also
        --------
        numpy.mastack: Function used.
        """
        return np.ma.stack(arrays, axis=axis, out=out)


class VariableMasked(Variable):
    """Variable subclass for masked data.

    Rely on numpy masked array.
    """

    acs = AccessorMask  #: Accessor class to use to access the data.

    def set_mask(self, mask: Union[Array, bool, int]):
        """Set mask to variable data.

        :param mask: Potential mask. If bool or int, a mask array is filled with
            this value. Can be array like (ndarray, tuple, list) with shape of
            the data. 0's are interpreted as False, everything else as True.

        :raises IndexError: Mask does not have the shape of the data.
        """
        self.check_loaded()

        if isinstance(mask, (bool, int)):
            mask_array = np.ma.make_mask_none(self.shape)
            mask_array |= mask
        else:
            mask_array = np.ma.make_mask(mask, shrink=None)

        if self.acs.shape(mask_array) != self.shape:
            raise IndexError("Mask has incompatible shape ({}, expected {})"
                             .format(self.acs.shape(mask_array), self.shape))
        self.data.mask = mask_array

    def filled(self, fill: Union[str, float] = 'fill_value',
               **keys: KeyLike) -> np.ndarray:
        """Return data with filled masked values.

        :param fill: If float, that value is used as fill. If 'nan', numpy.nan
            is used. If 'fill_value', the array fill value is used (default).
        """
        data = self.view(**keys)
        if fill == 'nan':
            fill_value = np.nan
        elif fill == 'fill_value':
            fill_value = self.data.fill_value
        else:
            fill_value = fill
        return data.filled(fill_value)

    def get_coverage(self, *dims: str) -> Union[Array, float]:
        """Return percentage of not masked values.

        :param dims: Coordinates to compute the coverage along.
            If None, all coordinates are taken.

        Examples
        --------
        >>> print(dt.get_coverage())
        70.

        If there is a time variable, we can have the coverage
        for each time step.

        >>> print(dt.get_coverage('lat', 'lon'))
        array([80.1, 52.6, 45.0, ...])
        """
        if not dims:
            dims = self.dims
        axis = [self.dims.index(c) for c in dims]

        size = 1
        for c in dims:
            size *= self._db.loaded[c].size

        cover = np.sum(~self[:].mask, axis=tuple(axis))
        return cover / size * 100
