"""Example from tutorial."""

from tomate import Coord, Time, Constructor
from tomate.filegroup import FilegroupNetCDF

import tomate.db_types as dt
import tomate.scan_library as scanlib


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
cstr.set_scan_variables_attributes(scanlib.nc.scan_variables_attributes)


# SST
coords_fg = [[lon, 'in'], [lat, 'in'], [time, 'shared']]
cstr.add_filegroup(FilegroupNetCDF, coords_fg, name='SST', root='SST')

pregex = ('%(prefix)_'
          r'%(time:Y)%(time:doy:custom=\d\d\d:)_'
          r'%(time:Y:dummy)%(time:doy:custom=\d\d\d:dummy)'
          '%(suffix)')
replacements = {'prefix': 'SSH',
                'suffix': r'\.nc'}
cstr.set_fg_regex(pregex, **replacements)

cstr.set_variables_infile(SST='sst')
cstr.set_scan_in_file(scanlib.nc.scan_in_file, 'lon', 'lat')
cstr.set_scan_filename(scanlib.get_date_from_matches, 'time', only_value=True)

cstr.set_scan_general_attributes(scanlib.nc.scan_infos)
cstr.set_scan_variables_attributes(scanlib.nc.scan_variables_attributes)


cstr.set_data_types([dt.DataMasked, dt.DataPlot])

# Create database
db = cstr.make_data()

# Access attributes
print(db.vi.fullname)

# Load all SST
db.load(var='SST')

# Load first time step of SST and SSH
db.load(['SST', 'SSH'], time=0)

# Load a subpart of all variables.
# The variables order in data is reversed
db.load(['SSH', 'SST'], lat=slice(0, 500), lon=slice(200, 800))

print(db.data)
