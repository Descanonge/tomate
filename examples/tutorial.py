"""Example from tutorial."""

from data_loader import Coord, Time
from data_loader import Constructor
from data_loader.filegroup import FilegroupNetCDF
from data_loader.data_plot import DataPlot
from data_loader.masked import DataMasked

import data_loader.scan_library as scanlib


# Coordinates
lat = Coord('lat', None, fullname='Latitude')
lon = Coord('lon', None, fullname='Longitude')
time = Time('time', None, fullname='Time',
            units='hours since 1970-01-01 00:00:00')

coords = [lat, lon, time]


cstr = Constructor('/Data/', coords)


# Filegroups

#     Data
#     ├── SSH
#     │   ├── SSH_20070101.nc
#     │   ├── SSH_20070109.nc
#     │   └── ...
#     └── SST
#         ├── A_2007001_2010008.L3m_8D_sst.nc
#         ├── A_2007008_2010016.L3m_8D_sst.nc
#         └── ...

# SSH
contains = ['SSH']
coords_fg = [[lon, 'in', 'longitude'],
             [lat, 'in', 'latitude'],
             [time, 'shared']]
cstr.add_filegroup(FilegroupNetCDF, contains, coords_fg, root='SSH')

pregex = ('%(prefix)_'
          '%(time:x)%'
          '%(suffix)')
replacements = {'prefix': 'SSH',
                'suffix': r'\.nc'}
cstr.set_fg_regex(pregex, replacements)
cstr.set_variables_infile('ssh')
cstr.set_scan_in_file(scanlib.scan_in_file_nc, 'lat', 'lon', 'time')
cstr.set_scan_general_attributes(scanlib.scan_infos_nc)
cstr.set_scan_coords_attributes(scanlib.scan_units_nc, 'lat', 'lon', 'time')


# SST
contains = ['SST']
coords_fg = [[lon, 'in'], [lat, 'in'], [time, 'shared']]
cstr.add_filegroup(FilegroupNetCDF, contains, coords_fg, root='SST')

pregex = ('%(prefix)_'
          r'%(time:Y)%(time:doy:custom=\d\d\d:)_'
          r'%(time:Y:dummy)%(time:doy:custom=\d\d\d:dummy)'
          '%(suffix)')
replacements = {'prefix': 'SSH',
                'suffix': r'\.nc'}
cstr.set_fg_regex(pregex, replacements)
cstr.set_variables_infile('sst')
cstr.set_scan_in_file(scanlib.scan_in_file_nc, 'lon', 'lat')
cstr.set_scan_filename(scanlib.get_date_from_matches, 'time', only_value=True)
cstr.set_scan_general_attributes(scanlib.scan_infos_nc)
cstr.set_scan_variables_attributes(scanlib.scan_variables_attributes_nc)


# Create database
dt = cstr.make_data([DataPlot, DataMasked])


# Access attributes
print(dt.vi.fullname)

# Load all SST
dt.load(var='SST')

# Load first time step of SST and SSH
dt.load(['SST', 'SSH'], time=0)


# Load a subpart of all variables.
# The variables order in data is reversed
dt.load(['SSH', 'SST'], lat=slice(0, 500), lon=slice(200, 800))

print(dt.data)
