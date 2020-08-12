"""Scanning functions for netCDF files."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from os import path
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

try:
    import netCDF4 as nc
except ImportError:
    pass

import numpy as np

from tomate.constructor import Constructor
from tomate.coordinates.coord import Coord
from tomate.coordinates.coord_str import CoordStr
from tomate.coordinates.time import Time

from tomate.filegroup.coord_scan import CoordScan
from tomate.filegroup.scanner import make_scanner
from tomate.filegroup.filegroup_netcdf import FilegroupNetCDF
from tomate.var_types.variable_masked import VariableMasked
import tomate.db_types as dt

if TYPE_CHECKING:
    from tomate.data_base import DataBase


@make_scanner('in', ['values', 'in_idx'])
def scan_dims(cs: CoordScan, file: nc.Dataset,
              values: Optional[List[float]]) -> Tuple[List[float], List[int]]:
    """Scan netCDF file for coordinates values and in-file index.

    Convert time values to CS units. Variable name must
    be 'time'.
    """
    nc_var = file[cs.name]
    in_values = list(nc_var[:])
    in_idx = list(range(len(in_values)))
    return in_values, in_idx


@make_scanner('in', ['values', 'in_idx', 'dimensions'])
def scan_variables(cs: CoordScan, file: nc.Dataset,
                   values: List[float]) -> Tuple[List[str]]:
    """Scan netCDF file for variables."""
    variables = []
    dimensions = []
    for name, var in file.variables.items():
        if name not in file.dimensions:
            variables.append(name)
            dims = list(file[name].dimensions)
            dims = cs.filegroup.translate_dimensions(dims)
            dimensions.append(dims)
    return variables, variables, dimensions


def scan_variables_attributes(fg: FilegroupNetCDF, file: nc.Dataset,
                              variables: List[str]) -> Dict[str, Dict[str, Any]]:
    """Scan variables attributes in netCDF files."""
    attrs = {}
    for var in variables:
        attrs_var = {}
        nc_var = file[var]
        attributes = nc_var.ncattrs()
        for attr in attributes:
            attrs_var[attr] = nc_var.getncattr(attr)

        attrs[var] = attrs_var
    return attrs


def scan_variables_datatype(fg: FilegroupNetCDF, file: nc.Dataset,
                            variables: List[str],
                            override=True) -> Dict[str, Dict[str, str]]:
    """Scan variables datatype in netCDF files."""
    attrs = {}
    for var in variables:
        dtype = file[var].dtype

        if override:
            for attr in ['add_offset', 'scale_factor']:
                if attr in file[var].ncattrs():
                    new = np.dtype(type(file[var].getncattr(attr)))
                    if new.kind == 'f':
                        dtype = new

        attrs[var] = {'datatype': dtype.str}

        if ({'_FillValue', 'missing_value'} & set(list(file[var].ncattrs()))):
            attrs[var]['_var_class'] = VariableMasked
    return attrs


def scan_infos(fg: FilegroupNetCDF, file: nc.Dataset) -> Dict[str, Any]:
    """Scan for general attributes in a netCDF file."""
    infos = {}
    for name in file.ncattrs():
        value = file.getncattr(name)
        infos[name] = value
    return infos


def scan_units(cs: CoordScan, file: nc.Dataset) -> Dict[str, str]:
    """Scan for the units of the time variable."""
    nc_var = file[cs.name]
    units = nc_var.getncattr('units')
    return {'units': units}


def scan_file(filename) -> 'DataBase':
    """Scan a single for everything.

    You don't have to do a thing !
    """
    with nc.Dataset(filename, 'r') as file:
        coords = []
        for dim in file.dimensions:
            if dim == 'time' and 'units' in file['time'].__dict__:
                coord = Time(dim, None, units=file['time'].units)
            elif file[dim].dtype is str:
                coord = CoordStr(dim)
            else:
                coord = Coord(dim)
            coords.append(coord)

    coords_name = [c.name for c in coords]

    cstr = Constructor(path.dirname(filename), coords)
    coords_fg = [cstr.CSS(c) for c in coords]
    cstr.add_filegroup(FilegroupNetCDF, coords_fg)

    cstr.current_fg.file_override = path.basename(filename)
    cstr.add_scan_in_file(scan_dims, *coords_name)
    cstr.add_scan_in_file(scan_variables, 'var')
    cstr.add_scan_general_attributes(scan_infos)
    cstr.add_scan_variables_attributes(scan_variables_attributes)
    cstr.add_scan_variables_attributes(scan_variables_datatype)

    cstr.set_data_types([dt.DataCompute, dt.DataPlot])

    db = cstr.make_data()

    return db
