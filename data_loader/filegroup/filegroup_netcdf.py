"""Filegroup class for netCDF files.

Basic support fillValue
"""

import logging
import warnings

import numpy as np
import netCDF4 as nc

from data_loader.filegroup.filegroup_load import FilegroupLoad

log = logging.getLogger(__name__)


class FilegroupNetCDF(FilegroupLoad):
    """An ensemble of files.

    For NetCDF files.
    """

    def _load_cmd(self, cmd):
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
        with nc.Dataset(cmd.filename, 'r') as data_file:
            log.info("Opening %s", cmd.filename)
            for var in cmd.var_list:
                ncname = self.get_ncname(var)
                i_var = self.db.vi.idx[var]

                for key_in, key_slice in cmd:
                    D = self._load_slice_single_var(data_file, key_in, ncname)

                    log.info("placing it in %s, (%s)", key_slice.values(), self.db.coords_name)
                    self.db.data[i_var][tuple(key_slice.values())] = D

                    # TODO: call a specialized function of self.db
                    # to account for different db types
                    self.db.data.mask[i_var][tuple(key_slice.values())] = D.mask

            # Make sure it is correctly masked
                try:
                    # TODO: getattr
                    data_file[ncname]._FillValue
                except AttributeError:
                    self.db.data.mask[i_var] = ~np.isfinite(self.db.data[i_var].data)

    def _load_slice_single_var(self, data_file, keys, ncname):
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

        order, keys_ = self._get_order(data_file, ncname, keys)

        log.info("taking keys %s", keys_)
        D = data_file[ncname][keys_]

        # If we ask for keys that are not in the file.
        # Add None keys to create axis in the array where needed
        for k in keys:
            if k not in order:
                D = np.expand_dims(D, -1)

        # Reorder array
        target = [self.db.coords_name.index(z) for z in order]
        log.info("reordering %s", target)
        D = np.moveaxis(D, range(len(order)), target)

        return D

    def _get_order(self, data_file, ncname, keys):
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
        order_nc = list(data_file[ncname].dimensions)
        order = []
        keys_ = []
        for coord_nc in order_nc:
            try:
                coord = self.db.get_coord(coord_nc)
            except KeyError:
                dim = data_file.dimensions[coord_nc].size
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
        try:
            ncname = self.db.vi.ncname[var]
        except AttributeError:
            ncname = None

        if ncname is None:
            ncname = var
        return ncname

    def write(self, filename, wd, variables, keys):
        """Write data to disk."""
        log.warning("Writing a subset not implemented, writing all data.")
       
        with nc.Dataset(wd + filename, 'w') as dt:
            log.info("in %s", filename)
            for name, coord in self.db.coords.items():
                dt.createDimension(name, coord.size)
                dt.createVariable(name, 'f', [name])
                dt[name][:] = coord[:]
                log.info("laying %s values, extent %s", name, coord.get_extent_str())

                dt[name].setncattr('fullname', coord.fullname)
                dt[name].setncattr('unit', coord.unit)

            for var in variables:
                name = self.get_ncname(var)
                try:
                    t = self.db.vi.type[var]
                except AttributeError:
                    t = 'f'
                dt.createVariable(var, t, self.db.coords_name)
                dt[var][:] = self.db.data[self.db.vi.idx[var]]

                for info in self.db.vi._infos:
                    dt[var].setncattr(info, self.db.vi.__getattribute__(info)[var])
