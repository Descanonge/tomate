"""Masked data classes."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


import logging

import numpy as np

from data_loader.data_base import DataBase
from data_loader.accessor import Accessor
from data_loader.keys.keyring import Keyring

import data_loader.db_types.masked.mask


log = logging.getLogger(__name__)


class AccessorMask(Accessor):
    """Accessor for masked numpy array."""

    @staticmethod
    def allocate(shape):
        array = np.ma.zeros(shape)
        array.mask = np.ma.make_mask_none(shape)
        return array

    @staticmethod
    def concatenate(arrays, axis=0):
        """Concatenate arrays.

        Parameters
        ----------
        array: List[Array]
        axis: int, optional
            The axis along which the arrays will be joined.
            If None, the arrays are flattened.

        Returns
        -------
        Array
        """
        return np.ma.concatenate(arrays, axis=axis)


class DataMasked(DataBase):
    """Encapsulate data array and info about the variables.

    For masked data.

    See :class:`DataBase` for more information.

    Attributes
    ----------
    compute_land_mask_func: Callable
        Function to compute land mask.
    """

    acs = AccessorMask

    def __init__(self, *args, **kwargs):
        self.compute_land_mask_func = None
        super().__init__(*args, **kwargs)

    def set_mask(self, variable, mask):
        """Set mask to variable data.

        Parameters
        ----------
        variable: str
        mask: Array, bool, int
            Potential mask.
            If bool or int, a mask array is filled with this value.
            Array like (ndarray, tuple, list) with shape of the data
            without the variable dimension.
            0's are interpreted as False, everything else as True.

        Raises
        ------
        IndexError:
            Mask does not have the shape of the data.
        """
        self.check_loaded()

        if isinstance(mask, (bool, int)):
            mask_array = np.ma.make_mask_none(self.shape[1:])
            mask_array ^= mask
        else:
            mask_array = np.ma.make_mask(mask, shrink=None)

        if list(mask_array.shape) != self.shape[1:]:
            raise IndexError("Mask has incompatible shape"
                             "(%s, expected %s)" % (list(mask_array.shape),
                                                    self.shape[1:]))
        self[variable].mask = mask_array

    def filled(self, fill, variables=None, axes=None, **kw_coords):
        """Return data with filled masked values.

        Parameters
        ----------
        fill: Any
            If float, that value is used as fill.
            If 'nan', numpy.nan is used.
            If 'fill_value', the array fill value is used.
            If 'edge', the closest pixel value is used.
        """
        data = self.view(variables, **kw_coords)
        if fill == 'edge':
            filled = data_loader.db_types.masked.mask.fill_edge(data, axes)
        else:
            if fill == 'nan':
                fill_value = np.nan
            elif fill == 'fill_value':
                fill_value = self.data.fill_value
            else:
                fill_value = fill
            filled = data.filled(fill_value)
        return filled

    def get_coverage(self, variable, *coords):
        """Return percentage of not masked values for a variable.

        Parameters
        ----------
        variable: str
        coords: str, optional
            Coordinates to compute the coverage along.
            If None, all coordinates are taken.

        Examples
        --------
        >>> print(dt.get_coverage('SST'))
        70%

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

    def mask_nan(self, missing=True, inland=True, coast=5, chla=True):
        """Replace sst and chla-OC5 fill values by nan.

        Parameters
        ----------
        missing: bool, optional
            Mask not valid.
        inland: bool, optional
            Mask in land.
        coast: int, optional
            If inland, mask `coast` neighbooring pixels.
        chla: bool, optional
            Clip Chlorophyll above 3mg.m-3 and under 0.

        Raises
        ------
        RuntimeError
            If data was not previously loaded.
        """
        if self.data is None:
            raise RuntimeError("Data has not been previously loaded.")

        if missing:
            m = ~np.isfinite(self.data)
            self.data.mask |= m

        if inland:
            m = self.get_land_mask()
            if coast > 0:
                m = data_loader.db_types.masked.mask.enlarge_mask(m, coast)
            self.data.mask |= m

        if chla:
            A = self.data[self.idx('Chla_OC5')]
            A = np.clip(A, 0, 3)
            self.data[self.idx('Chla_OC5')] = A
            # A[A > 3] = np.nan

    def set_compute_land_mask(self, func):
        """Set function to compute land mask.

        Parameters
        ----------
        func: Callable[[lat: Coord, lon: Coord],
                       [mask: 2D numpy bool array]]
             Returns a land mask as a boolean array.
        """
        self.compute_land_mask_func = func

    def compute_land_mask(self):
        """Compute land mask and save to disk."""
        lat = self.avail.lat
        lon = self.avail.lon
        mask = self.compute_land_mask_func(lat, lon)
        np.save(self.root + 'land_mask.npy', mask)

    def get_land_mask(self, keyring=None, **keys):
        """Return land mask.

        Parameters
        ----------
        keyring: Keyring
        keys: Key-like

        Returns
        -------
        mask: np.array(dtype=bool)
        """
        keyring = Keyring.get_default(keyring, **keys)
        # TODO: subset of land mask default to loaded or selected
        try:
            file = np.load(self.root + 'land_mask.npy',
                           mmap_mode='r')
        except FileNotFoundError:
            self.compute_land_mask()
            self.get_land_mask()
        else:
            mask = self.acs.take(file, keyring)

        return mask
