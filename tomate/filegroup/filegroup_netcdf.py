"""NetCDF files support."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import logging
import os
from typing import Any, Dict, List

try:
    import netCDF4 as nc
except ImportError:
    _has_netcdf = False
else:
    _has_netcdf = True

import numpy as np

from tomate.accessor import Accessor
from tomate.custom_types import File, KeyLike
from tomate.keys.keyring import Keyring
from tomate.filegroup.filegroup_load import FilegroupLoad
from tomate.filegroup.command import separate_variables, Command


log = logging.getLogger(__name__)


class FilegroupNetCDF(FilegroupLoad):
    """Filegroup class for NetCDF files."""

    acs = Accessor

    def __init__(self, *args, **kwargs):
        if not _has_netcdf:
            raise ImportError("netCDF4 package necessary to use FilegroupNetCDF.")
        super().__init__(*args, **kwargs)

    def open_file(self, filename: str,
                  mode: str = 'r',
                  log_lvl: str = 'info',
                  **kwargs: Any) -> 'nc.Dataset':
        kwargs.setdefault('clobber', False)
        file = nc.Dataset(filename, mode, **kwargs)

        log_lvl = getattr(logging, log_lvl.upper())
        log.log(log_lvl, "Opening %s", filename)
        return file

    def close_file(self, file: File):
        file.close()

    def get_commands(self, keyring: Keyring, memory: Keyring) -> List[Command]:
        commands = super().get_commands(keyring, memory)
        commands = separate_variables(commands)
        return commands

    def load_cmd(self, file: File, cmd: Command):
        for krg_inf, krg_mem in cmd:
            for ncname in krg_inf['var']:
                log.info("Looking at variable %s", ncname)

                chunk = self._load_slice_single_var(file, krg_inf, ncname)

                log.info("Placing it in %s",
                         krg_mem.print())
                self.db.acs.place(krg_mem, self.db.data, chunk)

    def _load_slice_single_var(self, file: 'nc.Dataset',
                               keyring: Keyring, ncname: str) -> np.ndarray:
        """Load data for a single variable.

        :param file: File object.
        :param keyring: Keys to load from file.
        :param ncname: Name of the variable in file.
        """
        order_file = self._get_order_in_file(file, ncname)
        order = self._get_order(order_file)
        int_krg = self._get_internal_keyring(order, keyring)

        log.info("Taking keys %s", int_krg.print())
        chunk = self.acs.take_normal(int_krg, file[ncname])

        chunk_shape = self.db.acs.shape(chunk)
        if not int_krg.is_shape_equivalent(self.db.acs.shape(chunk)):
            raise ValueError("Data taken from file has not expected shape"
                             " (is {}, excepted {})"
                             .format(chunk_shape, int_krg.shape))

        chunk = self.reorder_chunk(chunk, keyring, int_krg)
        return chunk

    @staticmethod
    def _get_order_in_file(file: 'nc.Dataset', ncname: str) -> List[str]:
        """Get order from netcdf file, reorder keys.

        :param file: File object.
        :param ncname: Name of the variable in file.

        :returns: Coordinate names in order.
        """
        order = list(file[ncname].dimensions)
        return order

    def write(self, filename: str, wd: str = None,
              file_kw: Dict = None, var_kw: Dict[str, Dict] = None,
              keyring: Keyring = None, **keys: KeyLike):
        """Write data to disk.

        The filegroups should have their variable scanning
        coordinate setup correctly. See :func:`FilegroupLoad.write
        <tomate.filegroup.filegroup_load.FilegroupLoad.write>`.

        Variable specific arguments are passed to `netCDF.Dataset.createVariable
        <https://unidata.github.io/netcdf4-python/netCDF4/index.html
        #netCDF4.Dataset.createVariable>`__. If the 'datatype' argument is
        not specified, the 'datatype' attribute is looked in the VI, and if
        not defined, it is guessed from the numpy array dtype.

        If the 'fill_value' attribute is not specifed, the '_FillValue'
        attribute is looked in the VI, and if not defined
        `netCDF4.default_fillvals(datatype)` is used. It seems preferable
        to specify a fill_value rather than None.

        All attributes from the VariablesInfo are put in the file if their
        name do not start with an '_'.

        :param wd: Directory to place the file. If None, the
            filegroup root is used instead.
        :param file_kw: Keywords argument to pass to `open_file`.
        :param var_kw: Variables specific arguments.
        """
        if wd is None:
            wd = self.root
        filename = os.path.join(wd, filename)

        keyring = Keyring.get_default(keyring=keyring, **keys)

        if file_kw is None:
            file_kw = {}
        if var_kw is None:
            var_kw = {}

        file_kw.setdefault('mode', 'w')
        file_kw.setdefault('log_lvl', 'INFO')
        with self.open_file(filename, **file_kw) as file:
            for name, coord in self.db.loaded.coords.items():
                key = keyring[name].copy()
                key.set_shape_coord(coord)
                if key.shape != 0:
                    file.createDimension(name, key.shape)
                    file.createVariable(name, 'f', [name])
                    file[name][:] = coord[key.value]
                    log.info("Laying %s values, extent %s", name,
                             coord.get_extent_str(key.no_int()))

                    file[name].setncattr('fullname', coord.fullname)
                    file[name].setncattr('units', coord.units)

            for var in keyring['var']:
                cs = self.cs['var']
                name = cs.in_idx[cs.idx(var)]

                dimensions = keyring.get_non_zeros()
                dimensions.remove('var')

                kwargs = var_kw.get(var, {})

                datatype = kwargs.pop('datatype', None)
                if datatype is None:
                    datatype = self.vi.get_attr_safe('datatype', var, None)
                    if datatype is None:
                        dtype = self.db.data.dtype
                        datatype = '{}{}'.format(dtype.kind, dtype.itemsize)

                if 'fill_value' not in kwargs:
                    if '_FillValue' in self.vi[var]:
                        kwargs['fill_value'] = self.vi[var]._FillValue
                    else:
                        kwargs['fill_value'] = nc.default_fillvals.get(datatype, None)

                file.createVariable(name, datatype, dimensions, **kwargs)
                file[name][:] = self.db.view(keyring=keyring, var=var)

            self._add_vi_to_file(file, keyring)

    def _add_vi_to_file(self, file, keyring):
        """Add metadata from VI to file."""
        for info in self.db.vi.infos:
            if not info.startswith('_'):
                file.setncattr(info, self.db.vi.get_info(info))

        for var in keyring['var']:
            cs = self.cs['var']
            name = cs.in_idx[cs.idx(var)]
            if var in self.db.vi.variables:
                attrs = self.db.vi[var]
                for attr in attrs:
                    if not attr.startswith('_'):
                        file[name].setncattr(attr, self.db.vi.get_attr(attr, var))

    def write_variable(self, file: 'nc.Dataset', cmd: Command,
                       var: str, inf_name: str):
        """Add variable to file."""

        for krg_inf, krg_mem in cmd:
            if inf_name not in file.variables:

                t = self.vi.get_attr_safe('nctype', var, 'f')
                file.createVariable(inf_name, t, self.db.coords)

                for attr in self.db.vi.attrs:
                    if not attr.startswith('_'):
                        value = self.db.vi.get_attr(attr, var)
                        if value is not None:
                            file[inf_name].setncattr(attr, value)

            ncvar = file[var]

            order = self._get_order_in_file(file, var)
            chunk = self.db.acs.take(krg_mem, self.db.data)
            chunk = self.reorder_chunk(chunk, krg_inf, order)

            if not krg_inf.is_shape_equivalent(ncvar.shape):
                raise ValueError("Mismatch between selected data "
                                 "and keyring shape (array: {}, keyring: {})"
                                 .format(ncvar.shape, krg_inf.shape))
            ncvar[:] = chunk
