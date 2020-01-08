"""Data class for netCDF files."""

import logging

import numpy as np

from data_loader.data_base import DataBase
import data_loader.masked.mask


log = logging.getLogger(__name__)


class DataMasked(DataBase):
    """Encapsulate data array and info about the variables.

    For masked data.

    Data and coordinates can be accessed with getter:
    Data[{name of variable | name of coordinate}]

    Data is loaded from disk with load_data.

    Attributes
    ----------
    compute_land_mask_func: Callable
        Function to compute land mask.
    """
    def __init__(self, *args, **kwargs):
        self.compute_land_mask_func = None

        super().__init__(*args, **kwargs)

    def allocate_memory(self, shape):
        """Allocate data variable.

        Data is storred as a masked array
        """
        log.info("Allocating numpy masked array of shape %s", shape)
        data = np.ma.zeros(shape)
        data.mask = np.ma.make_mask_none(shape)
        return data

    def set_mask(self, variable, mask):
        """Set mask to variable data.

        Parameters
        ----------
        variable: str
        mask: Array like, bool, int
            Potential mask.
            If bool or int, a mask array is filled.
            Array like (ndarray, tuple, list) with shape of the data
            without the variable dimension.
            0's are interpreted as False, everything else as True.

        Raises
        ------
        IndexError:
            Mask does not have the shape of the data.
        """
        self._check_loaded()

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

    def get_coverage(self, variable, *coords):
        """Return percentage of not masked values for a variable.

        Parameters
        ----------
        variable: str
        coords: List[str]
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
            coords = self.coords_name
        axis = [self.coords_name.index(c) for c in coords]

        size = 1
        for c in coords:
            size *= self.coords[c].size

        cover = np.sum(~self[variable].mask, axis=tuple(axis))
        return cover / size * 100

    def mask_nan(self, missing=True, inland=True, coast=5, chla=True):
        """Replace sst and chla-OC5 fill values by nan.

        Parameters
        ----------
        missing: bool, True
            Mask not valid.
        inland: bool, True
            Mask in land.
        coast: int, 5
            If inland, mask `coast` neighbooring pixels.
        chla: bool, True
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
                m = data_loader.masked.mask.enlarge_mask(m, coast)
            self.data.mask |= m

        if chla:
            A = self.data[self.vi.idx['Chla_OC5']]
            A = np.clip(A, 0, 3)
            self.data[self.vi.idx['Chla_OC5']] = A
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
        lat, lon = self.get_coords_from_backup('lat', 'lon')
        mask = self.compute_land_mask_func(lat, lon)
        np.save(self.root + 'land_mask.npy', mask)

    def get_land_mask(self, keys=None):
        """Return land mask.

        Parameters
        ----------
        keys: List[numpy keys]

        Returns
        -------
        mask: np.array(dtype=bool)
        """
        if keys is None:
            keys = [self.slices[c] for c in ['lat', 'lon']]

        try:
            mask = np.load(self.root + 'land_mask.npy',
                           mmap_mode='r')[tuple(keys)]
        except FileNotFoundError:
            self.compute_land_mask()
            self.get_land_mask()

        return mask
