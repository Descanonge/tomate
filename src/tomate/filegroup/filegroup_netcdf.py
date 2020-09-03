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

from tomate.accessor import Accessor
from tomate.custom_types import File
from tomate.coordinates.coord_str import CoordStr
from tomate.filegroup.filegroup_load import FilegroupLoad
from tomate.filegroup.command import Command, CmdKeyrings


log = logging.getLogger(__name__)


class FilegroupNetCDF(FilegroupLoad):
    """Filegroup class for NetCDF files.

    Accessor is normal accessor for numpy arrays. But we only use `take_normal`
    since the python-netcdf4 api handles it well.
    """

    acs = Accessor

    def __init__(self, *args, **kwargs):
        if not _has_netcdf:
            raise ImportError("netCDF4 package necessary to use FilegroupNetCDF.")
        super().__init__(*args, **kwargs)

    def open_file(self, filename: str, mode: str = 'r',
                  log_lvl: str = 'info', **kwargs: Any) -> 'nc.Dataset':
        kwargs.setdefault('clobber', False)
        file = nc.Dataset(filename, mode, **kwargs)

        log_lvl = getattr(logging, log_lvl.upper())
        log.log(log_lvl, "Opening %s", filename)
        return file

    def close_file(self, file: File):
        file.close()

    def load_cmd(self, file: File, cmd: Command):
        for krg_inf, krg_mem in cmd:
            name = krg_mem.pop('var').value
            ncname = krg_inf.pop('var').value

            log.info("Taking keys %s from variable %s",
                     krg_inf.print(), ncname)
            chunk = self.acs.take_normal(krg_inf, file[ncname])

            chunk_shape = self.acs.shape(chunk)
            if not krg_inf.is_shape_equivalent(self.acs.shape(chunk)):
                raise ValueError("Data taken from file has not expected shape"
                                 " (is {}, excepted {})"
                                 .format(chunk_shape, krg_inf.shape))

            chunk = self.acs.reorder(krg_inf.get_non_zeros(), chunk,
                                     krg_mem.get_non_zeros(), log_lvl='INFO')

            log.info("Placing it in %s, %s", name, krg_mem.print())
            self.db.variables[name].set_data(chunk, krg_mem)

    def _write(self, file: nc.Dataset, cmd: Command, var_kw: Dict):

        def add_coord(name, mem):
            coord = self.db.loaded.coords[name]
            if name in self.cs:
                ncname = self.cs[name].name
            else:
                ncname = name

            key = mem[name].copy()
            key.set_size_coord(coord)
            if key.size != 0:
                file.createDimension(ncname, key.size)
                if isinstance(coord, CoordStr):
                    file.createVariable(ncname, 'S2', [ncname])
                    for i, v in enumerate(coord[:]):
                        file[ncname][i] = v
                else:
                    file.createVariable(ncname, 'f', [ncname])
                    file[ncname][:] = coord[key.value]
                log.info("Laying %s values, extent %s", name,
                         coord.get_extent_str(key.no_int()))

                file[ncname].setncattr('fullname', coord.fullname)
                file[ncname].setncattr('units', coord.units)

        self.add_vi_to_file(file, add_attr=False)

        dims = {'var'}
        for inf, mem in cmd:
            for dim in set(inf) - dims:
                dims.add(dim)
                add_coord(dim, mem)

        for cmd_krgs in cmd:
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
            :func:`FilegroupLoad.write
            <tomate.filegroup.filegroup_load.FilegroupLoad.write>`.
        :raises IndexError: If mismatch between memory keyring and in-file
            dimensions list.
        """
        krg_inf, krg_mem = cmd
        name = self.db.loaded.var.get_str_name(krg_mem.pop('var').value)
        ncname = krg_inf.pop('var').value
        log.info('Inserting variable %s', ncname)

        kwargs = var_kw.get('_all', {})
        kwargs.update(var_kw.get(name, {}))
        kwargs = kwargs.copy()

        if ncname not in file.variables:
            datatype = kwargs.pop('datatype', None)
            if datatype is None:
                datatype = self.db.variables[name].datatype

            if 'fill_value' not in kwargs:
                if self.vi.has(name, '_FillValue'):
                    kwargs['fill_value'] = self.vi.get_attribute(name, '_FillValue')
                else:
                    kwargs['fill_value'] = nc.default_fillvals.get(datatype, None)

            dimensions = kwargs.pop('dimensions', krg_inf.get_non_zeros())
            if 'var' in dimensions:
                dimensions.remove('var')

            dimensions = self.translate_dimensions(dimensions, True)
            file.createVariable(ncname, datatype, dimensions, **kwargs)
        else:
            log.info('Variable already exist. Overwriting data.')

        self.add_vi_to_file(file, add_info=False,
                            name=name, ncname=ncname)

        order = self.translate_dimensions(list(file[ncname].dimensions))
        if order != krg_inf.get_non_zeros():
            raise IndexError("File dimensions ({}) length does not"
                             " match keyring length ({})"
                             .format(order, krg_mem.get_non_zeros()))

        chunk = self.db.variables[name].view(keyring=krg_mem, order=order,
                                             log_lvl='INFO')

        log.info("Placing it in file at %s.", krg_inf.print())
        self.acs.place_normal(krg_inf, file[ncname], chunk)

    def translate_dimensions(self, dimensions: List[str],
                             reverse: bool = False) -> List[str]:
        """Translate dimensions as they appear in file to in database."""
        if not reverse:
            rosetta = {c.name: c.coord.name for c in self.cs.values()}
        else:
            rosetta = {c.coord.name: c.name for c in self.cs.values()}
        translate = [rosetta[d] if d in rosetta else d for d in dimensions]
        return translate
