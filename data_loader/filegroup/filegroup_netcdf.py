"""Filegroup class for netCDF files.

Basic support fillValue
"""

import logging

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
        cmd: Command
            Load command containing the filename,
            variables to load, in file keys, and
            where to place the data.
        """
        with nc.Dataset(cmd.filename, 'r') as data_file:
            log.info("Opening %s", cmd.filename)
            for var in cmd.var_list:
                ncname = self.get_ncname(var)
                i_var = self.db.vi.idx[var]
                log.info("variable %s", ncname)

                for keys_inf, keys_mem in cmd:
                    chunk = self._load_slice_single_var(data_file, keys_inf, ncname)

                    log.info("placing it in %s",
                             [i_var] + list(keys_mem.values()))
                    self.db.data[i_var][tuple(keys_mem.values())] = chunk

                # # Make sure it is correctly masked
                # try:
                #     data_file[ncname].getncattr("_FillValue")
                # except AttributeError:
                #     self.db.data.mask[i_var] = ~np.isfinite(self.db.data[i_var].data)

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

        order, keys_inf = self._get_order(data_file, ncname, keys)

        log.info("taking keys %s", list(keys_inf.values()))
        chunk = data_file[ncname][keys_inf.values()]
        chunk = self._reorder_chunk(order, keys, chunk)

        return chunk

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
        keys_ord: Dict
            Keys ordered
        """
        order_nc = list(data_file[ncname].dimensions)
        order = []
        keys_ord = {}
        for coord_nc in order_nc:
            try:
                coord = self.db.get_coord(coord_nc)
            except KeyError:
                dim = data_file.dimensions[coord_nc].size
                if dim > 1:
                    log.warning("Additional dimension %s in file of "
                                "size > 1. The first index will be used",
                                coord)
                name = coord_nc
                k = 0
                # We do not keep the coord name in `order` for a key equal to zero,
                # numpy will squeeze the axis.
            else:
                name = coord.name
                k = keys[name]
                order.append(name)

            keys_ord[name] = k
        return order, keys_ord

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
        # FIXME: Coordinate descending !
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

                for info in self.db.vi.infos:
                    dt[var].setncattr(info, self.db.vi.__getattribute__(info)[var])
