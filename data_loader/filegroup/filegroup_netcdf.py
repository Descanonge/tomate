"""Filegroup class for netCDF files."""

import logging

import netCDF4 as nc

from data_loader.filegroup.filegroup_load import FilegroupLoad


log = logging.getLogger(__name__)


class FilegroupNetCDF(FilegroupLoad):
    """Filegroup class for NetCDF files."""

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
            i_var = self.db.vi.idx[var]
            log.info("Looking at variable %s", ncname)

            for keys_inf, keys_mem in cmd:
                chunk = self._load_slice_single_var(file, keys_inf, ncname)

                log.info("Placing it in %s",
                         [i_var] + list(keys_mem.values()))
                self.db.data[i_var][tuple(keys_mem.values())] = chunk

    def _load_slice_single_var(self, file, keys, ncname):
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

        order, keys_inf = self._get_order(file, ncname, keys)

        log.info("Taking keys %s", list(keys_inf.values()))
        chunk = file[ncname][keys_inf.values()]
        chunk = self.reorder_chunk(chunk, keys, order, variables=False)

        return chunk

    def _get_order(self, file, ncname, keys):
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
        keys_ord = {}
        for coord_nc in order_nc:
            try:
                coord = self.db.get_coord(coord_nc)
            except KeyError:
                dim = file.dimensions[coord_nc].size
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
        """Get the infile variable name.

        Try to get it in the `ncname` attribute
        in the vi. If not present, or None, the
        variable name is used.
        """
        try:
            ncname = self.vi.ncname[var]
        except KeyError:
            ncname = None

        if ncname is None:
            ncname = var
        return ncname

    def write(self, filename, wd, variables, keys):
        """Write data to disk."""
        log.warning("Writing a subset not implemented, writing all data.")

        with self.open_file(filename, mode='w') as dt:
            log.info("in %s", filename)
            for name, coord in self.db.coords.items():
                dt.createDimension(name, coord.size)
                dt.createVariable(name, 'f', [name])
                dt[name][:] = coord[:]
                log.info("Laying %s values, extent %s", name, coord.get_extent_str())

                dt[name].setncattr('fullname', coord.fullname)
                dt[name].setncattr('units', coord.units)

            for var in variables:
                name = self.get_ncname(var)
                try:
                    t = self.db.vi.type[var]
                except AttributeError:
                    t = 'f'
                dt.createVariable(var, t, self.db.coords_name)
                dt[var][:] = self.db.data[self.db.vi.idx[var]]

                for attr in self.db.vi.attrs:
                    dt[var].setncattr(attr, self.db.vi.get_attr(attr, var))
