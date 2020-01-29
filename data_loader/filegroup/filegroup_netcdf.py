"""Filegroup class for netCDF files."""

import logging
import os

try:
    import netCDF4 as nc
except ImportError:
    _has_netcdf = False
else:
    _has_netcdf = True

from data_loader.filegroup.filegroup_load import FilegroupLoad
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

    def open_file(self, filename, mode='r', log_lvl='info'):
        file = nc.Dataset(filename, mode)
        log_lvl = getattr(logging, log_lvl.upper())
        log.log(log_lvl, "Opening %s", filename)
        return file

    def close_file(self, file):
        file.close()

    def load_cmd(self, file, cmd):
        """Load data from one file using a command.

        Parameters
        ----------
        cmd: Command
            Load command containing the filename,
            variables to load, in file keys, and
            where to place the data.
        """
        for var in cmd.var_list:
            ncname = self.get_ncname(var)
            i_var = self.db.loaded.idx[var]
            log.info("Looking at variable %s", ncname)

            for krg_inf, krg_mem in cmd:
                chunk = self._load_slice_single_var(file, krg_inf, ncname)

                log.info("Placing it in %s",
                         [i_var] + krg_mem.keys_values)
                self.acs.place(krg_mem, self.db.data[i_var], chunk)

    def _load_slice_single_var(self, file, keyring, ncname):
        """Load data for a single variable.

        Parameters
        ----------
        file: nc.Dataset
            File object.
        keys: Dict[coord name: str, key: slice or List[int]]
            Keys to load in file.
        order: List[str]
            Order of dimensions in file.
        ncname: str
            Name of the variable in file.
        """

        order, krg_inf = self._get_order(file, ncname, keyring)

        log.info("Taking keys %s", krg_inf.keys_values)
        chunk = self.acs.take(krg_inf, file[ncname])

        krg_inf.set_shape(self.db.avail.subset(krg_inf.coords))
        expected_shape = krg_inf.shape
        assert (expected_shape == list(chunk.shape)), ("Chunk does not have correct "
                                                       "shape, has %s, expected %s"
                                                       % (list(chunk.shape), expected_shape))

        chunk = self.reorder_chunk(chunk, keyring.coords, order, variables=False)
        return chunk

    def _get_order(self, file, ncname, keyring):
        """Get order from netcdf file, reorder keys.

        Parameters
        ----------
        file: nc.Dataset
             File object.
        ncname: str
             Name of the variable in ile.
        keys: Dict[coord name: str, key: slice or List[int]]
            Keys to load in file.

        Returns
        -------
        order: List[str]
            Coordinate names in order.
        keys_ord: Dict
            Keys in order.
        """
        order_nc = list(file[ncname].dimensions)
        order = []
        keys_ord = Keyring()
        for coord_nc in order_nc:
            try:
                name = self.db.get_coord_name(coord_nc)
            # If the demanded coord is not in file
            except KeyError:
                dim = file.dimensions[coord_nc].size
                if dim > 1:
                    log.warning("Additional dimension %s in file of "
                                "size > 1. The first index will be used",
                                coord_nc)
                name = coord_nc
                k = 0
                # We do not keep the coord name in `order` for a key equal to zero,
                # numpy will squeeze the axis.
            else:
                k = keyring[name]
                order.append(name)

            keys_ord[name] = k
        return order, keys_ord

    def get_ncname(self, var: str) -> str:
        """Get the infile variable name.

        Try to get it in the `ncname` attribute
        in the vi. If not present, or None, the
        variable name is used.
        """
        ncname = self.vi.get_attr_safe('ncname', var)

        if ncname is None:
            ncname = var
        return ncname

    def write(self, filename, wd, variables, keys):
        """Write data to disk."""
        log.warning("Writing a subset not implemented, writing all data.")

        file = os.path.join(wd, filename)

        with self.open_file(file, mode='w') as dt:
            log.info("in %s", file)
            for name, coord in self.db.coords.items():
                dt.createDimension(name, coord.size)
                dt.createVariable(name, 'f', [name])
                dt[name][:] = coord[:]
                log.info("Laying %s values, extent %s", name, coord.get_extent_str())

                dt[name].setncattr('fullname', coord.fullname)
                dt[name].setncattr('units', coord.units)

            for info in self.db.vi.infos:
                if not info.startswith('_'):
                    dt.setncattr(info, self.db.vi.get_info(info))

            for var in variables:
                name = self.get_ncname(var)
                try:
                    t = self.db.vi.nctype[var]
                except AttributeError:
                    t = 'f'
                dt.createVariable(var, t, self.db.coords_name)
                dt[var][:] = self.db[var]

                for attr in self.db.vi.attrs:
                    if not attr.startswith('_'):
                        dt[var].setncattr(attr, self.db.vi.get_attr(attr, var))
