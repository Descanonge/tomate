"""A example of typical database creation script.

This script presents an efficient way of creating a database and
be able to re-use it in other scripts.

One can either use `db = get_data()` to directly import use the database object,
or could instead do `cstr = get_cstr()` to retrieve the Constructor
and do additional operation on it, like adding a filegroup with another
function similar to `add_sst`.

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
    cstr.set_data_types([dt.DataCompute, dt.DataPlot])

    add_sst(cstr)

    return cstr


def add_sst(cstr):
    coords_fg = [cstr.CSS('lat', name='latitude'),
                 cstr.CSS('lon', name='longitude'),
                 cstr.CSS('time', 'shared')]
    cstr.add_filegroup(FilegroupNetCDF, coords_fg, name='SST', root='SST')
    cstr.set_fg_regex(r'SST_%(time:x)\.nc')

    cstr.add_scan_in_file(scanlib.nc.scan_variables, 'var')

    cstr.add_scan_filename(scanlib.get_date_from_matches, 'time')
    cstr.set_elements_constant('time', in_idx=0)
    cstr.add_scan_in_file(scanlib.nc.scan_dims, 'lat', 'lon')

    cstr.add_scan_variables_attributes(scanlib.nc.scan_variables_attributes)
    cstr.add_scan_variables_attributes(scanlib.nc.scan_variables_datatype)
    cstr.set_scan_general_attributes(scanlib.nc.scan_infos)

    cstr.add_post_loading_func(K2C, 'SST')


def K2C(db):
    """Convert from Kelvin to Celsius"""
    db['SST'][:] += 273.15
    db.vi.set_attributes('SST', units='°C')
