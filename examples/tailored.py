"""A example of typical database creation script.

This script presents an efficient way of creating a database and
be able to re-use it in other scripts.

One can either use `db = get_data()` to directly import use the database object,
or could instead do `cstr = get_cstr()` to retrieve the Constructor
and do additional operation on it, like adding a filegroup with another
function similar to `add_ssh`.

This can be used to combine multiple data.
"""

from tomate import Lat, Lon, Time, Constructor
from tomate.filegroup import FilegroupNetCDF

import tomate.db_types as dt
import tomate.scan_library as scanlib

root = '/Data/'


def get_data():
    cstr = get_cstr()
    db = cstr.make_data()
    return db


def get_cstr():
    time = Time('time', None, 'hours since 1970-01-01 00:00:00')
    lat = Lat()
    lon = Lon()

    cstr = Constructor('Data', [time, lat, lon])
    cstr.set_data_types([dt.DataMasked, dt.DataCompute])

    add_ssh(cstr)

    return cstr


def add_ssh(cstr):
    [time, lat, lon] = [cstr.coords[c] for c in ['time', 'lat', 'lon']]

    coords_fg = [[lon, 'in', 'longitude'],
                 [lat, 'in', 'latitude'],
                 [time, 'shared']]
    cstr.add_filegroup(FilegroupNetCDF, coords_fg, name='SSH', root='SSH')

    pregex = ('%(prefix)_'
              '%(time:x)%'
              '%(suffix)')
    replacements = {'prefix': 'SSH',
                    'suffix': r'\.nc'}
    cstr.set_fg_regex(pregex, **replacements)

    cstr.set_variables_infile(SSH='sea surface height')
    cstr.set_scan_in_file(scanlib.nc.scan_in_file, 'lat', 'lon', 'time')

    cstr.set_scan_coords_attributes(scanlib.nc.scan_units, 'time')
    cstr.set_scan_general_attributes(scanlib.nc.scan_infos)
