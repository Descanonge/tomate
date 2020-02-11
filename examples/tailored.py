"""A example of tailored database.

This package offers an important feature: if the different
filegroups have distinct ranges, only the overlap is loaded.
However it is sometime useful to load everything available for
one filegroup.

This example show how this can be easily achieved.
It uses the same kind of data as the tutorial.
Separate functions are used to add a single filegroup
and the corresponding variables.

The use of a hidden `_get_data` function encapsulated
into a public `get_data` is suggested so that the
content of `get_data` can be replicated into a
section executed if the file is run, and this with
a minimal amount of redondant code.
The public function can be easily imported into others
scripts, and the module can be run directly to debug
the database creation (in which case the constructor
is directly available).

It is also suggested to implement keyword arguments
that can be passed to the `add_...` function, to have
even more options for loading slightly different data
at runtime.
Here the source of the SSH data can be picked at runtime.
"""

from data_loader import Coord, Time
from data_loader import Constructor
from data_loader.filegroup import FilegroupNetCDF
from data_loader.masked import DataMasked
import data_loader.scan_library as scanlib

__all__ = ['get_data']

root = '/Data/'

time = Time('time', None, 'hours since 1970-01-01 00:00:00')
lat = Coord('lat', None, 'deg', 'latitude', 'Latitude')
lon = Coord('lon', None, 'deg', 'longitude', 'Longitude')

coords = [time, lat, lon]


def add_ssh(cstr, source):
    """Add the SSH to the VI and filegroups."""
    name = "SSH"
    attrs = {'fullname': 'Sea Surface Height',
             'ncname': 'ssh'}
    cstr.add_variable(name, **attrs)

    contains = ['SSH']
    coords_fg = [[lon, 'in'], [lat, 'in'], [time, 'shared']]
    cstr.add_filegroup(FilegroupNetCDF, contains, coords_fg, root=source+'SSH')

    pregex = ('%(prefix)_'
              '%(time:Y)%(time:mm)%(time:dd)'
              '%(suffix)')
    replacements = {'prefix': 'SSH',
                    'suffix': r'\.nc'}
    cstr.set_fg_regex(pregex, replacements)

    cstr.set_scan_in_file_func(scanlib.scan_in_file_nc, 'lat', 'lon', 'time')
    cstr.set_scan_attribute_func(scanlib.scan_attributes_nc)


def add_sst(cstr):
    """Add the SST to the VI and filegroups."""

    name = "SST"
    attrs = {'fullname': 'Sea Surface Temperature',
             'ncname': 'sst',
             'unit': 'deg C',
             'vmin': -2, 'vmax': 30}
    cstr.add_variable(name, **attrs)

    contains = ['SST']
    coords_fg = [[lon, 'in'], [lat, 'in'], [time, 'shared']]
    cstr.add_filegroup(FilegroupNetCDF, contains, coords_fg, root='SST')

    pregex = ('%(prefix)_'
              r'%(time:Y)%(time:doy:custom=\d\d\d:)_'
              r'%(time:Y:dummy)%(time:doy:custom=\d\d\d:dummy)'
              '%(selfuffix)')
    replacements = {'prefix': 'SSH',
                    'suffix': r'\.nc'}
    cstr.set_fg_regex(pregex, replacements)

    cstr.set_scan_in_file_func(scanlib.scan_in_file_nc, 'lon', 'lat')
    cstr.set_scan_filename_func(scanlib.get_date_from_matches, 'time')
    cstr.set_scan_attribute_func(scanlib.scan_attributes_nc)

def _get_data(cstr, groups, **kwargs):
    if groups is None:
        groups = ["SSH", "SST"]

    kwargs_default = {'source': 'MODIS'}
    kwargs_default.update(kwargs)
    kwargs = kwargs_default

    if "SSH" in groups:
        add_ssh(cstr, kwargs['source'])
    if "SST" in groups:
        add_sst(cstr)

    dt = cstr.make_database(DataMasked)
    return dt


def get_data(groups=None, **kwargs):
    """Return a data object.

    The filegroups and variables to add can be
    tailored using groups.
    """
    cstr = Constructor(root, coords)
    dt = _get_data(cstr, groups, **kwargs)
    return dt


if __name__ == '__main__':
    cstr = Constructor(root, coords)
    dt = _get_data(cstr, ["SSH", "SST"])
