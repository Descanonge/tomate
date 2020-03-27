"""NetCDF files support."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


import logging
import os

try:
    import netCDF4 as nc
except ImportError:
    _has_netcdf = False
else:
    _has_netcdf = True

from data_loader.filegroup.filegroup_load import FilegroupLoad
from data_loader.filegroup.command import separate_variables
from data_loader.key import Keyring


log = logging.getLogger(__name__)


class FilegroupNetCDF(FilegroupLoad):
    """Filegroup class for NetCDF files.

    Parameters
    ----------
    args, kwargs
        Passed to FilegroupLoad.
        See FilegroupScan for init.
    """

    def __init__(self, *args, **kwargs):
        if not _has_netcdf:
            raise ImportError("netCDF4 package necessary to use FilegroupNetCDF.")
        super().__init__(*args, **kwargs)

    def open_file(self, filename, mode='r', log_lvl='info') -> nc.Dataset:
        file = nc.Dataset(filename, mode)
        log_lvl = getattr(logging, log_lvl.upper())
        log.log(log_lvl, "Opening %s", filename)
        return file

    def close_file(self, file):
        file.close()

    def get_commands(self, keyring):
        commands = super().get_commands(keyring)
        commands = separate_variables(commands)
        return commands

    def load_cmd(self, file, cmd):
        """Load data from one file using a command.

        Parameters
        ----------
        file: netCDF4.Dataset
        cmd: Command
            Load command containing the filename,
            variables to load, in file keys, and
            where to place the data.
        """
        for krg_inf, krg_mem in cmd:
            for ncname in krg_inf['var']:
                log.info("Looking at variable %s", ncname)

                chunk = self._load_slice_single_var(file, krg_inf, ncname)

                log.info("Placing it in %s",
                         krg_mem.print())
                self.acs.place(krg_mem, self.db.data, chunk)

    def _load_slice_single_var(self, file, keyring, ncname):
        """Load data for a single variable.

        Parameters
        ----------
        file: nc.Dataset
            File object.
        keyring: Keyring
            Keys to load from file.
        ncname: str
            Name of the variable in file.
        """
        order = self._get_order(file, ncname)
        int_krg = self._get_internal_keyring(order, keyring)

        log.info("Taking keys %s", int_krg.print())
        chunk = self.acs.take(int_krg, file[ncname])

        dims = list(keyring.dims)
        dims.remove('var')
        chunk = self.reorder_chunk(chunk, dims, order, variables=False)
        return chunk

    def _get_order(self, file, ncname):
        """Get order from netcdf file, reorder keys.

        Parameters
        ----------
        file: nc.Dataset
             File object.
        ncname: str
             Name of the variable in ile.

        Returns
        -------
        order: List[str]
            Coordinate names in order.
        """
        order_nc = list(file[ncname].dimensions)
        order = []
        for coord_nc in order_nc:
            try:
                name = self.db.get_coord_name(coord_nc)

            # If the demanded dimension is not in database.
            except KeyError:
                dim = file.dimensions[coord_nc].size
                if dim > 1:
                    log.warning("Additional dimension %s in file of "
                                "size > 1. The first index will be used",
                                coord_nc)
                name = coord_nc
                # We do not keep the coord name in `order` for a key equal to zero,
                # numpy will squeeze the axis.
            else:
                order.append(name)

        return order

    def write(self, filename, wd, keyring):
        """Write data to disk."""
        if wd is None:
            wd = self.root

        file = os.path.join(wd, filename)

        with self.open_file(file, mode='w') as dt:
            log.info("in %s", file)
            for name, coord in self.db.loaded.coords.items():
                key = keyring[name].copy()
                key.set_shape_coord(coord)
                if key.shape != 0:
                    dt.createDimension(name, key.shape)
                    dt.createVariable(name, 'f', [name])
                    dt[name][:] = coord[key.value]
                    log.info("Laying %s values, extent %s", name,
                             coord.get_extent_str(key.no_int()))

                    dt[name].setncattr('fullname', coord.fullname)
                    dt[name].setncattr('units', coord.units)

            for info in self.db.vi.infos:
                if not info.startswith('_'):
                    dt.setncattr(info, self.db.vi.get_info(info))

            for var in keyring['var']:
                cs = self.cs['var']
                name = cs.in_idx[cs.idx(var)]
                t = self.vi.get_attr_safe('nctype', var, 'f')
                dt.createVariable(name, t, self.db.coords_name)
                dt[name][:] = self.db.view(keyring, var=var)

                for attr in self.db.vi.attrs:
                    if not attr.startswith('_'):
                        dt[name].setncattr(attr, self.db.vi.get_attr(attr, var))

    def write_variable(self, file, cmd, var, inf_name):

        for krg_inf, krg_mem in cmd:
            if inf_name not in file.variables:

                t = self.vi.get_attr_safe('nctype', var, 'f')
                file.createVariable(inf_name, t, self.db.coords_name)

                for attr in self.db.vi.attrs:
                    # TODO: no attributes for all variables.
                    if not attr.startswith('_'):
                        value = self.db.vi.get_attr(attr, var)
                        if value is not None:
                            file[inf_name].setncattr(attr, value)

            ncvar = file[var]

            order = self._get_order(file, var)
            chunk = self.db.acs.take(krg_mem, self.db.data)
            chunk = self.reorder_chunk(chunk, krg_inf, order)

            self.db.acs.check_shape_none(krg_inf, ncvar.shape)
            ncvar[:] = chunk
