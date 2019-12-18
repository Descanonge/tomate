"""Function for scanning filenames and files."""

from datetime import datetime, timedelta

import netCDF4 as nc


def get_value_from_matches(cs):
    """Retrieve value from matches.

    matchers: list of matchers object
    coord: coord name
    """
    elts = {z.elt: z.match for z in cs.matchers if not z.dummy}

    value = elts.get("value")
    if value is not None:
        return float(value)

    idx = elts.get("idx")
    if idx is not None:
        return int(idx)

    return None


def get_date_from_matches(cs):
    """Retrieve date from matched elements.

    Default date is 1970-01-01 12:00:00
    If any element is not found in the filename, it will be
    replaced by that element in the default date.
    If no match is found, None is returned.
    """
    elts = {z.elt: z.match for z in cs.matchers if not z.dummy}

    match = False
    date = {"year": 1970, "month": 1, "day": 1,
            "hour": 12, "minute": 0, "second": 0}

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
        return nc.date2num(datetime(**date), cs.unit)

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

def scan_in_file_nc(cs, filename, values): #pylint: disable=unused-argument
    """Scan netCDF file for inout values."""
    with nc.Dataset(filename, 'r') as dt:
        for name in [cs.name] + cs.name_alt:
            try:
                in_values = dt[name][:]
            except IndexError:
                in_values = None
                in_idx = None
            else:
                in_values = list(in_values)
                in_idx = list(range(len(in_values)))
                break

    return in_values, in_idx


def scan_in_file_nc_idx_only(cs, filename, values):
    """Scan netCDF for inout index only."""
    _, in_idx = scan_in_file_nc(cs, filename, values)
    return values, in_idx


def scan_attribute_nc(fg, filename, variables):
    """Scan for all attributes in a netCDF file."""

    infos = {}
    with nc.Dataset(filename, 'r')as dt:
        for var in variables:
            infos_var = {}
            nc_var = dt[fg.get_ncname(var)]
            attributes = nc_var.ncattrs()
            for attr in attributes:
                infos_var[attr] = nc_var.getncattr(attr)

            infos[var] = infos_var

    return infos
