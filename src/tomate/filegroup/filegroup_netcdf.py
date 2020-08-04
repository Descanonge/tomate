"""NetCDF files support."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import logging
from typing import Any, Dict, List

try:
    import netCDF4 as nc
except ImportError:
    _has_netcdf = False
else:
    _has_netcdf = True

import numpy as np

from tomate.accessor import Accessor
from tomate.custom_types import File
from tomate.keys.keyring import Keyring
from tomate.filegroup.filegroup_load import FilegroupLoad
from tomate.filegroup.command import separate_variables, Command, CmdKeyrings


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
            name = krg_mem.pop('var').value
            ncname = krg_inf['var'].value
            log.info("Looking at variable %s", ncname)

            chunk = self._load_slice_single_var(file, krg_inf, ncname)

            log.info("Placing it in %s",
                     krg_mem.print())
            self.db.variables[name].set_data(chunk, krg_mem)

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

        chunk_shape = self.acs.shape(chunk)
        if not int_krg.is_shape_equivalent(self.acs.shape(chunk)):
            raise ValueError("Data taken from file has not expected shape"
                             " (is {}, excepted {})"
                             .format(chunk_shape, int_krg.shape))

        chunk = self.reorder_chunk(chunk, keyring, int_krg)
        return chunk

    @staticmethod
    def _get_order_in_file(file: 'nc.Dataset' = None,
                           var_name: str = None) -> List[str]:
        """Get order from netcdf file, reorder keys.

        :param file: File object.
        :param inf_name: Name of the variable in file.
        :returns: Coordinate names in order.
        """
        order = list(file[var_name].dimensions)
        return order

    def _write(self, file: nc.Dataset, cmd: Command, var_kw: Dict):
        self.add_vi_to_file(file, add_attr=False)

        for name, coord in self.db.loaded.coords.items():
            key = cmd[0].memory[name].copy()
            key.set_size_coord(coord)
            if key.size != 0:
                file.createDimension(name, key.size)
                file.createVariable(name, 'f', [name])
                file[name][:] = coord[key.value]
                log.info("Laying %s values, extent %s", name,
                         coord.get_extent_str(key.no_int()))

                file[name].setncattr('fullname', coord.fullname)
                file[name].setncattr('units', coord.units)

        cmd_var, = separate_variables([cmd])
        for cmd_krgs in cmd_var:
            self.add_variables_to_file(file, cmd_krgs, **var_kw)

    def add_vi_to_file(self, file, add_info=True, add_attr=True,
                       name=None, ncname=None):
        """Add metada to file."""
        if add_info:
            for info in self.vi.infos:
                if not info.startswith('_'):
                    value = self.db.vi.get_info(info)
                    try:
                        file.setncattr(info, value)
                    except TypeError:
                        file.setncattr(info, str(value))
        if add_attr:
            if name in self.vi.variables:
                attrs = self.vi[name]
                for attr in attrs:
                    if not attr.startswith('_'):
                        value = self.vi.get_attribute(name, attr)
                        try:
                            file[ncname].setncattr(attr, value)
                        except TypeError:
                            file[ncname].setncattr(attr, str(value))

    def add_variables_to_file(self, file: 'nc.Dataset', cmd: CmdKeyrings,
                              **var_kw: Dict[str, Dict]):
        """Add variables data and metadata to file.

        If a variable already exist in file, its data is overwritten.
        In which case there could be discrepancies in dimensions ordering,
        proceed with caution.

        :param cmd: Load command. Variables must be separated.
        :param var_kw: [opt] Variables specific argument. See
            `FilegroupNetCDF.write`.
        :raises IndexError: If mismatch between memory keyring and
            in-file dimensions list.
        """
        krg_inf, krg_mem = cmd
        name = self.db.loaded.var.get_str_name(krg_mem['var'].value)
        ncname = krg_inf['var'].value
        log.info('Inserting variable %s', ncname)

        kwargs = var_kw.get('_all', {})
        kwargs.update(var_kw.get(name, {}))
        kwargs = kwargs.copy()

        if ncname not in file.variables:
            datatype = kwargs.pop('datatype', None)
            if datatype is None:
                datatype = self.db.variables[name].datatype
            try:
                kwargs.setdefault('fill_value',
                                  self.vi.get_attribute(name, '_FillValue'))
            except KeyError:
                kwargs.setdefault('fill_value',
                                  nc.default_fillvals.get(datatype, None))

            dimensions = kwargs.pop('dimensions', krg_inf.get_non_zeros())
            if 'var' in dimensions:
                dimensions.remove('var')

            file.createVariable(ncname, datatype, dimensions, **kwargs)
        else:
            log.info('Variable already exist. Overwriting data.')

        self.add_vi_to_file(file, add_info=False,
                            name=name, ncname=ncname)

        order_file = self._get_order_in_file(file, ncname)
        order = self._get_order(order_file)
        int_krg = self._get_internal_keyring(order, krg_inf)

        if len(order_file) != len(krg_mem.get_non_zeros()):
            raise IndexError("File dimensions ({}) length does not"
                             " match keyring length ({})"
                             .format(order_file, krg_mem.get_non_zeros()))

        chunk = self.db.view(keyring=krg_mem)
        chunk = self.reorder_chunk(chunk, krg_mem, int_krg)
        log.info("Placing it in file at %s.", int_krg.print())
        self.acs.place_normal(int_krg, file[ncname], chunk)
