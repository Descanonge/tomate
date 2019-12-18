"""Example from tutorial."""

from data_loader import Coord, Time
from data_loader.constructor import VIConstructor, FGConstructor
from data_loader.filegroup import FilegroupNetCDF
from data_loader.masked import DataMasked

import data_loader.scan_library as scanlib


root = "/home/clement/Documents/Stage/Data/Data_SOM/Data/8days/"

# Coordinates
lat = Coord('lat', None, fullname='Latitude', name_alt='latitude')
lon = Coord('lon', None, fullname='Longitude', name_alt='longitude')
time = Time('time', None, fullname='Time',
            unit='hours since 1970-01-01 00:00:00')

coords = [lat, lon, time]


# Variables
vic = VIConstructor()


name = "SSH"
infos = {'fullname': 'Sea Surface Height',
         'ncname': 'ssh'}
vic.add_var(name, infos)

vi = vic.make_vi()

name = "SST"
infos = {'fullname': 'Sea Surface Temperature',
         'ncname': 'sst',
         'unit': 'deg C',
         'vmin': -2, 'vmax': 30}
vic.add_var(name, infos)


# Filegroups
"""
    Data
    ├── SSH
    │   ├── SSH_20070101.nc
    │   ├── SSH_20070109.nc
    │   └── ...
    └── SST
        ├── A_2007001_2010008.L3m_8D_sst.nc
        ├── A_2007008_2010016.L3m_8D_sst.nc
        └── ...
"""
fgc = FGConstructor('/Data/', coords)

contains = ['SSH']
coords_fg = [[lon, 'in'], [lat, 'in'], [time, 'shared']]
fgc.add_fg(FilegroupNetCDF, contains, coords_fg)

pregex = ('%(dir)/%(prefix)_'
          '%(time:Y)%(time:mm)%(time:dd)'
          '%(suffix)')
replacements = {'dir': 'SSH/',
                'prefix': 'SSH',
                'suffix': r'\.nc'}
fgc.set_fg_regex(pregex, replacements)

fgc.set_scan_in_file_func(scanlib.scan_in_file_nc, 'lat', 'lon', 'time')


contains = ['SST']
coords_fg = [[lon, 'in'], [lat, 'in'], [time, 'shared']]
fgc.add_fg(FilegroupNetCDF, contains, coords_fg)

pregex = ('%(dir)/%(prefix)_'
          r'%(time:Y)%(time:doy:custom=\d\d\d:)_'
          r'%(time:Y:dummy)%(time:doy:custom=\d\d\d:dummy)'
          '%(suffix)')
replacements = {'dir': 'SSH/',
                'prefix': 'SSH',
                'suffix': r'\.nc'}
fgc.set_fg_regex(pregex, replacements)

fgc.set_scan_in_file_func(scanlib.scan_in_file_nc, 'lon', 'lat')
fgc.set_scan_filename_func(scanlib.get_date_from_matches, 'time')

dt = fgc.make_database(DataMasked, vi)

# Load all SST
dt.load_data('SST')

# Load first time step of SST and SSH
dt.load_data(['SST', 'SSH'], time=0)
dt.load_data(None, 0)

# Load a subpart of all variables.
# The variables order in data is reversed
dt.load_data(['SSH', 'SST'], lat=slice(0, 500), lon=slice(200, 800))

print(dt.data)
