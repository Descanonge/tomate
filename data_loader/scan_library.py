"""Function for scanning filenames and files."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta

import netCDF4 as nc

from data_loader.coordinates.time import Time
from data_loader.filegroup.coord_scan import CoordScan
from data_loader.filegroup.filegroup_netcdf import FilegroupNetCDF


def get_date_from_matches(cs: CoordScan,
                          values: Optional[List[float]],
                          default_date: Dict = None) -> Tuple[Optional[float], None]:
    """Retrieve date from matched elements.

    If any element is not found in the filename, it will be
    replaced by that element in the default date.
    If no match is found, None is returned.

    The date is converted to CoordScan units, or if not specified its parent
    Coord units.

    :param default_date: Default date element.
        Defaults to 1970-01-01 12:00:00
    """
    date = {"year": 1970, "month": 1, "day": 1,
            "hour": 12, "minute": 0, "second": 0}

    if default_date is None:
        default_date = {}
    date.update(default_date)

    elts = {z.elt: z.match for z in cs.matchers if not z.dummy}

    match = False

    y = elts.pop("x", None)
    if y is not None:
        match = True
        date["year"] = int(y[:4])
        date["month"] = int(y[4:6])
        date["day"] = int(y[6:8])

    y = elts.pop("Y", None)
    if y is not None:
        match = True
        date["year"] = int(y)

    y = elts.pop("yy", None)
    if y is not None:
        match = True
        date["year"] = int("20"+y)

    M = elts.pop("M", None)
    if M is not None:
        M = _find_month_number(M)
        if M is not None:
            match = True
            date["month"] = M

    m = elts.pop("mm", None)
    if m is not None:
        match = True
        date["month"] = int(m)

    d = elts.pop("dd", None)
    if d is not None:
        match = True
        date["day"] = int(d)

    d = elts.pop("doy", None)
    if d is not None:
        match = True
        doy = datetime(date["year"], 1, 1) + timedelta(days=int(d)-1)
        date["month"] = doy.month
        date["day"] = doy.day

    # TODO: add hours

    if match:
        return nc.date2num(datetime(**date), cs.units), None

    return None, None


def get_value_from_matches(cs: CoordScan,
                           values: Optional[List[float]]) -> Tuple[Optional[int], None]:
    """Retrieve value from matches."""
    elts = {z.elt: z.match for z in cs.matchers if not z.dummy}

    value = elts.get("value")
    if value is not None:
        return float(value), None

    idx = elts.get("idx")
    if idx is not None:
        return int(idx), None

    return None, None

def get_string_from_match(cs: CoordScan,
                          values: Optional[List[float]]) -> Tuple[Optional[str]]:
    """Retrieve string from match.

    Take first not dummy match of element 'text' or 'char'.
    """
    for m in cs.matchers:
        if not m.dummy and m.elt in ['text', 'char']:
            return m.match, m.match
    return None, None

def _find_month_number(name: str) -> Optional[int]:
    """Find a month number from its name.

    name can be the full name (January)
    or its three letter abbreviation (jan.)
    The casing does not matter
    """
    names = ['january', 'february', 'march', 'april',
             'may', 'june', 'july', 'august', 'september',
             'october', 'november', 'december']
    names_abbr = [c[:3] for c in names]

    name = name.lower()
    if name in names:
        return names.index(name)
    if name in names_abbr:
        return names_abbr.index(name)

    return None

def scan_in_file_nc(cs: CoordScan, file: nc.Dataset,
                    values: Optional[List[float]]) -> Tuple[List[float], List[int]]:
    """Scan netCDF file for coordinates values and in-file index.

    Convert time values to CS units. Variable name must
    be 'time'.
    """
    nc_var = file[cs.name]
    in_values = list(nc_var[:])
    in_idx = list(range(len(in_values)))
    return in_values, in_idx


def scan_variables_nc(cs: CoordScan, file: nc.Dataset,
                      values: List[float]) -> Tuple[List[str]]:
    """Scan netCDF file for variables names."""
    variables = [var for var in file.variables.keys()
                 if var not in cs.filegroup.cs.keys()]
    return variables, variables


def scan_variables_attributes_nc(fg: FilegroupNetCDF, file: nc.Dataset,
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


def scan_infos_nc(fg: FilegroupNetCDF, file: nc.Dataset) -> Dict[str, Any]:
    """Scan for general attributes in a netCDF file."""
    infos = {}
    for name in file.ncattrs():
        value = file.getncattr(name)
        infos[name] = value
    return infos


def scan_units_nc(cs: CoordScan, file: nc.Dataset) -> Dict[str, str]:
    """Scan for the units of the time variable."""
    nc_var = file[cs.name]
    units = nc_var.getncattr('units')
    return {'units': units}
