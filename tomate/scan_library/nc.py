"""Scanning functions for netCDF files."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import Any, Dict, List, Optional, Tuple

import netCDF4 as nc

from tomate.filegroup.coord_scan import CoordScan
from tomate.filegroup.filegroup_netcdf import FilegroupNetCDF


def scan_in_file(cs: CoordScan, file: nc.Dataset,
                 values: Optional[List[float]]) -> Tuple[List[float], List[int]]:
    """Scan netCDF file for coordinates values and in-file index.

    Convert time values to CS units. Variable name must
    be 'time'.
    """
    nc_var = file[cs.name]
    in_values = list(nc_var[:])
    in_idx = list(range(len(in_values)))
    return in_values, in_idx


def scan_variables(cs: CoordScan, file: nc.Dataset,
                   values: List[float]) -> Tuple[List[str]]:
    """Scan netCDF file for variables names."""
    variables = [var for var in file.variables.keys()
                 if var not in file.dimensions]
    return variables, variables


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
