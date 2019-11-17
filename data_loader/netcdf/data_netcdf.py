"""Data class for netCDF files.

Basic support fillValue

Contains
--------
DataNetCDF
"""

import warnings
from typing import List

import numpy as np
import netCDF4 as nc

from data_loader._data_base import _DataBase
import data_loader.netcdf.mask


class DataNetCDF(_DataBase):
    """Encapsulate data array and info about the variables.

    For NetCDF files.

    Data and coordinates can be accessed with subscript
    Data[{name of variable | name of coordinate}]

    Data is loaded from disk with load_data
    """

    def _allocate_memory(self):
        """Allocate data variable.

        Data is storred as a masked array
        """
        self.data = np.ma.zeros(self.shape)
        # TODO: Better api from numpy ?
        self.data.mask = np.ma.make_mask_none(self.shape)

    def _load_cmd(self, filename, var_list, keys_in, keys_slice):
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

                D = self._load_slice_single_var(dt, keys_in, ncname)

                i_var = self.vi.idx[var]
                self.data[i_var][tuple(keys_slice.values())] = D
                self.data.mask[i_var][tuple(keys_slice.values())] = D.mask

                # Make sure it is correctly masked
                try:
                    dt[ncname]._FillValue
                except AttributeError:
                    self.data.mask[i_var] = ~np.isfinite(self.data[i_var].data)

    def _load_slice_single_var(self, dt, keys, ncname):
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

        order, keys_ = self._get_order(dt, ncname, keys)

        D = dt[ncname][keys_]

        # If we ask for keys that are not in the file.
        # Add None keys to create axis in the array where needed
        for k in keys:
            if k not in order:
                D = np.expand_dims(D, -1)

        # Reorder array
        target = [self.coords_name.index(z) for z in order]
        D = np.moveaxis(D, range(len(order)), target)

        return D

    def _get_order(self, dt, ncname, keys):
        """Get order from netcdf file, reorder keys.

        Parameters
        ----------
        dt: nc.Dataset
        ncname: str
        keys: List[NpIdx]

        Returns
        -------
        order: List[str]
            Coordinate names in order
        """
        order_nc = list(dt[ncname].dimensions)
        order = []
        keys_ = []
        for coord_nc in order_nc:
            try:
                coord = self.get_coord(coord_nc)
            except KeyError:
                dim = dt.dimensions[coord_nc].size
                if dim > 1:
                    warnings.warn("Additional dimension {0} in file of "
                                  "size > 1. The first index will be used".format(coord))
                k = 0
                # We do not keep the coord name in order, with a key equal to zero,
                # numpy will squeeze the axis.
            else:
                k = keys[coord.name]
                order.append(coord.name)

            keys_.append(k)
        return order, keys_

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
                m = data_loader.netcdf.mask.enlarge_mask(m, coast)
            self.data.mask |= m

        if chla:
            A = self.data[self.vi.idx['Chla_OC5']]
            A = np.clip(A, 0, 3)
            self.data[self.vi.idx['Chla_OC5']] = A
            # A[A > 3] = np.nan

    def compute_land_mask(self):
        """Compute land mask and save to disk."""
        data_loader.netcdf.mask.compute_land_mask(
            self.root, self._coords_orr['lat'], self._coords_orr['lon'])

    def get_land_mask(self, keys=None):
        """Return land mask.

        Parameters
        ----------
        keys: List[NpIdx]

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

    def write(self, filename, wd=None, variables=None):
        """Write variables to disk.

        Write to a netcdf file.
        Coordinates are written too.

        Parameters
        ----------
        wd: str
            Directory. If None, `self.root` is used.
        variables: Union[List[str], str]
        filename: str
            If None, the first value of time is used.
        """

        if wd is None:
            wd = self.root

        if variables is None:
            variables = self.vi.var

        with nc.Dataset(wd + filename, 'w') as dt:
            for name, coord in self.coords.items():
                dt.createDimension(name, coord.size)
                dt.createVariable(name, 'f', [name])
                dt[name][:] = coord[:]

                dt[name].setncattr('fullname', coord.fullname)
                dt[name].setncattr('unit', coord.unit)

            for var in variables:
                name = self.get_ncname(var)
                try:
                    t = self.vi.type[var]
                except AttributeError:
                    t = 'f'
                dt.createVariable(var, t, self.coords_name)
                dt[var][:] = self[var]

                for info in self.vi._infos:
                    dt[var].setncattr(info, self.vi.__getattribute__(info)[var])
