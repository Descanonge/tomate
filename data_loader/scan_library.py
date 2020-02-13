"""Function for scanning filenames and files."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


from datetime import datetime, timedelta

import netCDF4 as nc

from data_loader.coordinates.time import change_units


def get_date_from_matches(cs, default_date=None):
    """Retrieve date from matched elements.

    If any element is not found in the filename, it will be
    replaced by that element in the default date.
    If no match is found, None is returned.

    Parameters
    ----------
    cs: CoordScan
    default_date: Dict, optional
        Default date element.
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
        return nc.date2num(datetime(**date), cs.units)

    return None


def get_value_from_matches(cs):
    """Retrieve value from matches."""
    elts = {z.elt: z.match for z in cs.matchers if not z.dummy}

    value = elts.get("value")
    if value is not None:
        return float(value)

    idx = elts.get("idx")
    if idx is not None:
        return int(idx)

    return None


def _find_month_number(name):
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

def scan_in_file_nc(cs, file, values): #pylint: disable=unused-argument
    """Scan netCDF file for coordinates values and in-file index.

    Convert time values to CS units. Variable name must
    be 'time'.
    """
    for name in [cs.name] + cs.name_alt:
        try:
            nc_var = file[name]
        except IndexError:
            in_values = None
            in_idx = None
        else:
            in_values = list(nc_var[:])
            in_idx = list(range(len(in_values)))

            if name == 'time':
                units = nc_var.getncattr('units')
                in_values = list(change_units(in_values, units, cs.units))
            break

    return in_values, in_idx


def scan_in_file_nc_idx_only(cs, file, values):
    """Scan netCDF for in-file index only."""
    _, in_idx = scan_in_file_nc(cs, file, values)
    return values, in_idx


def scan_attributes_nc(fg, file, variables):
    """Scan for variables attributes in a netCDF file."""
    attrs = {}
    for var in variables:
        attrs_var = {}
        nc_var = file[fg.get_ncname(var)]
        attributes = nc_var.ncattrs()
        for attr in attributes:
            attrs_var[attr] = nc_var.getncattr(attr)

        attrs[var] = attrs_var

    return attrs

def scan_infos_nc(fg, file):
    """Scan for general attributes in a netCDF file."""
    infos = {}
    for name in file.ncattrs():
        value = file.getncattr(name)
        infos[name] = value
    return infos


def scan_units_nc(cs, file):
    """Scan for the units of the time variable."""
    for name in [cs.name] + cs.name_alt:
        try:
            nc_var = file[name]
        except IndexError:
            units = None
        else:
            units = nc_var.getncattr('units')
            break

    return {'units': units}
