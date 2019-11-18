"""Function for scanning filenames and files."""

from datetime import datetime, timedelta

import netCDF4 as nc


def scan_filename_null(cs):
    """Null."""
    return None


def scan_in_file_null(cs, filename):
    """Null."""
    return None


def scan_inout_file_null(cs, filename, values):
    """Null."""
    return None, None


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


def get_date_from_matches(cs):
    """Retrieve date from matched elements."""
    elts = {z.elt: z.match for z in cs.matchers if not z.dummy}

    match = False
    date = {"year": 1970, "month": 1, "day": 1}

    y = elts.pop("Y", None)
    if y is not None:
        match = True
        date["year"] = int(y)

    y = elts.pop("yy", None)
    if y is not None:
        match = True
        date["year"] = int("20"+y)

    m = elts.pop("mm", None)
    if m is not None:
        match = True
        date["month"] = int(m)

    # TODO: month & day names

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


def scan_in_file_nc(cs, filename):
    """Scan netCDF file for in values."""
    with nc.Dataset(filename, 'r') as dt:
        for name in [cs.name] + cs.name_alt:
            try:
                values = dt[name][:]
            except IndexError:
                values = None
            else:
                break

    values = list(values)
    return values


def scan_inout_file_nc(cs, filename, values):
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

