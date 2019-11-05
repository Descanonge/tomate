"""Data class for netCDF files.

Basic support fillValue

Computation of land mask from Natural Earth using cartopy.

Contains
--------
DataNetCDF

Routines
--------
compute_land_mask
"""

from typing import List

import numpy as np
import netCDF4 as nc

import mypack.analysis as mpa

from ._data_base import _DataBase


class DataNetCDF(_DataBase):
    """Encapsulate data array and info about the variables.

    For NetCDF files.

    Data and coordinates can be accessed with subscript
    Data[{name of variable | name of coordinate}]

    Data is loaded from disk with load_data
    """

    def _allocate_memory(self, n_var: int, shape: List[int]):
        """Allocate data variable.

        Data is storred as a masked array
        """
        self.data = np.ma.zeros([n_var, *shape])

    def _load_cmd(self, filename, var_list, keys):
        """Load data from one file using a command.

        Parameters
        ----------
        filename: str
            Filename to open
        var_list: List[str]
            Variables to load
        keys: Dict[coord name, key]
            Keys to load in file
        """
        with nc.Dataset(filename, 'r') as dt:
            for var in var_list:
                ncname = self.get_ncname(var)

                order = self._get_order(dt, ncname)
                D = self._load_slice_single_var(dt, keys, order, ncname)

                i_var = self.vi.idx[var]
                self.data[i_var] = D

                # Make sure it is correctly masked
                try:
                    dt[ncname]._FillValue
                except AttributeError:
                    self.data.mask[i_var] = ~np.isfinite(self.data[i_var].data)

    def _load_slice_single_var(self, dt, keys, order, ncname):
        """Load data for a single variable.

        The data is reordered

        Parameters
        ----------
        dt: nc.Dataset
        keys: Dict[coord name, key]
        order: List[str]
            Order of coordinates in file
        ncname: str
            Name of the variable in file
        """

        # Reorder keys
        # Suppose the name of order are in the asked keys
        keys_ = [keys[z] for z in order]

        D = dt[ncname][keys_]

        # Add None keys to create axis in the array where needed
        for k in keys:
            if k not in order:
                keys_.append(None)
                order.append(k)
                D = np.expand_dims(D, -1)

        # Reorder array
        target = [self.coords_name.index(z) for z in order]
        D = np.moveaxis(D, range(len(order)), target)

        return D

    def _get_order(self, dt, ncname):
        """Get order from netcdf file.

        Parameters
        ----------
        dt: nc.Dataset
        ncname: str

        Returns
        -------
        order: List[str]
            Coordinate names in order
        """
        order = list(dt[ncname].dimensions)
        order = [self.get_coord(z).name for z in order]
        return order

    def get_ncname(self, var: str) -> str:
        """Get the infile name."""
        ncname = self.vi.ncname[var]
        if ncname is None:
            ncname = var
        return ncname

    def mask_nan(self, missing=True, inland=True, coast=5, chla=True):
        """Replace sst and chla-OC5 fill values by nan.

        Parameters
        ----------
        missing: bool, True
            Mask not valid
        inland: bool, True
            Mask in land
        coast: int, 5
            If inland, mask `coast` neighbooring pixels
        chla: bool, True
            Clip Chlorophyll above 3mg.m-3 and under 0

        Raises
        ------
        RuntimeError
            If data was not previously loaded
        """
        if self.data is None:
            raise RuntimeError("Data has not been previously loaded.")

        if missing:
            m = ~np.isfinite(self.data)
            self.data.mask |= m

        if inland:
            m = self.get_land_mask()
            if coast > 0:
                m = mpa.enlarge_mask(m, coast)
            self.data.mask |= m

        if chla:
            A = self.data[self.vi.idx['Chla_OC5']]
            A = np.clip(A, 0, 3)
            self.data[self.vi.idx['Chla_OC5']] = A
            # A[A > 3] = np.nan

    def compute_land_mask(self):
        """Compute land mask and save to disk."""
        # TODO: alt names
        compute_land_mask(self.root, self['lat'], self['lon'])

    def get_land_mask(self, keys=None):
        # FIXME
        """Return land mask.

        Parameters
        ----------
        keys: List[NpIdx]

        Returns
        -------
        mask: np.array(dtype=bool)
        """
        if keys is None:
            keys = slice(None, None)

        mask = np.load(self.root + 'land_mask.npy',
                       mmap_mode='r')[tuple(keys)]
        return mask


def compute_land_mask(root, lat, lon):
    """Compute land mask.

    According to Cartopy data (from naturalearthdata.com)
    for a regular grid save it in wd

    Parameters
    ----------
    root: str
        Directory
    lat: List[float]
    lon: List[float]
    """
    from shapely.ops import unary_union
    from cartopy.feature import LAND
    from shapely.geometry.polygon import Polygon

    # Extent
    d = (lon[-1]-lon[0])/10.
    lon_min = np.min(lon) - d
    lon_max = np.max(lon) + d
    lat_min = np.min(lat) - d
    lat_max = np.max(lat) + d
    extent = [(lon_min, lat_min), (lon_max, lat_min),
              (lon_max, lat_max), (lon_min, lat_max)]

    P = Polygon(extent)
    global_land = unary_union(tuple(LAND.geometries()))
    land = global_land.intersection(P)

    mask = mpa.rasterize(land, lon, lat)
    np.save(root + 'land_mask.npy', mask)
