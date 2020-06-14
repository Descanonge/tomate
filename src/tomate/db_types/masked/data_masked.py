"""Masked data classes."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import Callable, List, Union
import logging
import os.path

import numpy as np

from tomate.coordinates.coord import Coord
from tomate.custom_types import Array, KeyLike
from tomate.data_base import DataBase
from tomate.accessor import Accessor
from tomate.keys.keyring import Keyring

import tomate.db_types.masked.mask


log = logging.getLogger(__name__)


class AccessorMask(Accessor):
    """Accessor for masked numpy array."""

    @staticmethod
    def allocate(shape: List[int]) -> Array:
        array = np.ma.zeros(shape)
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


class DataMasked(DataBase):
    """Encapsulate data array and info about the variables.

    For masked data.

    See :class:`DataBase` for more information.

    :attr compute_land_mask_func: Callable: Function to compute land mask.
    """

    acs = AccessorMask  #: Accessor class to use to access the data.

    def __init__(self, *args, **kwargs):
        self.compute_land_mask_func = None
        super().__init__(*args, **kwargs)

    def set_mask(self, variable: str, mask: Union[Array, bool, int]):
        """Set mask to variable data.

        :param mask: Potential mask.
            If bool or int, a mask array is filled with this value.
            Array like (ndarray, tuple, list) with shape of the data
            without the variable dimension.
            0's are interpreted as False, everything else as True.

        :raises IndexError: Mask does not have the shape of the data.
        """
        self.check_loaded()

        if isinstance(mask, (bool, int)):
            mask_array = np.ma.make_mask_none(self.shape[1:])
            mask_array ^= mask
        else:
            mask_array = np.ma.make_mask(mask, shrink=None)

        if list(mask_array.shape) != self.shape[1:]:
            raise IndexError("Mask has incompatible shape ({}, expected {})"
                             .format(self.acs.shape(mask_array), self.shape[1:]))
        self[variable].mask = mask_array

    def filled(self, fill: Union[str, float] = 'fill_value',
               axes: List[int] = None,
               **keys: KeyLike) -> np.ndarray:
        """Return data with filled masked values.

        :param fill: If float, that value is used as fill.
            If 'nan', numpy.nan is used.
            If 'fill_value', the array fill value is used (default).
            If 'edge', the closest pixel value is used.
        :param axes: If `fill` is 'edge', the axes that should be
            used to fill values.
        """
        data = self.view(**keys)
        if fill == 'edge':
            filled = tomate.db_types.masked.mask.fill_edge(data, axes)
        else:
            if fill == 'nan':
                fill_value = np.nan
            elif fill == 'fill_value':
                fill_value = self.data.fill_value
            else:
                fill_value = fill
            filled = data.filled(fill_value)
        return filled

    def get_coverage(self, variable: str, *coords: str) -> Union[Array, float]:
        """Return percentage of not masked values for a variable.

        :param coords: Coordinates to compute the coverage along.
            If None, all coordinates are taken.

        Examples
        --------
        >>> print(dt.get_coverage('SST'))
        70.

        If there is a time variable, we can have the coverage
        for each time step.

        >>> print(dt.get_coverage('SST', 'lat', 'lon'))
        array([80.1, 52.6, 45.0, ...])
        """
        if not coords:
            coords = self.coords
        axis = [self.coords.index(c) for c in coords]

        size = 1
        for c in coords:
            size *= self.loaded[c].size

        cover = np.sum(~self[variable].mask, axis=tuple(axis))
        return cover / size * 100

    def set_compute_land_mask(self, func: Callable[[Coord, Coord], Array]):
        """Set function to compute land mask.

        Parameters
        ----------
        func: Function that receives latitude and longitude
             coordinates and returns a land mask as a boolean array.
        """
        self.compute_land_mask_func = func

    def compute_land_mask(self, file: str = None):
        """Compute land mask and save to disk.
        :param file: File to save the mask in. Absolute path.
            If None, is 'land_mask.npy' in the database root directory.
        """
        if file is None:
            file = os.path.join(self.root + 'land_mask.npy')
        lat = self.avail.lat
        lon = self.avail.lon
        mask = self.compute_land_mask_func(lat, lon)
        np.save(file, mask)

    def get_land_mask(self, file: str = None,
                      keyring: Keyring = None,
                      **keys: KeyLike) -> Array:
        """Return land mask.

        If not already on-disk at `file`, compute it.

        :param file: Numpy binary file containing the land mask.
            Filename is absolute.
            If None, is 'land_mask.npy' in the database root directory.
        """
        if file is None:
            file = os.path.join(self.root + 'land_mask.npy')

        keyring = Keyring.get_default(keyring, **keys)
        # TODO: subset of land mask default to loaded or selected
        try:
            file = np.load(file, mmap_mode='r')
        except FileNotFoundError:
            self.compute_land_mask()
            self.get_land_mask()
        else:
            mask = self.acs.take(file, keyring)

        return mask
