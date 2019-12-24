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

    def allocate_memory(self):
        """Allocate data variable.

        Uses the current variables and coordinates selection
        to get the needed shape.
        Data is storred as a masked array
        """
        log.info("Allocating numpy masked array of shape %s", self.shape)
        self.data = np.ma.zeros(self.shape)
        # TODO: Better api from numpy ?
        self.data.mask = np.ma.make_mask_none(self.shape)

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
