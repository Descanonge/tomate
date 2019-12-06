"""Module compiling filegroups type.

Contains
--------
FilegroupLoad
    Abstract class defining filegroups.

FilegroupNetCDF
    Filegroup class for netCDF files
"""



from .filegroup_load import FilegroupLoad
from .filegroup_netcdf import FilegroupNetCDF

__all__ = [
    'FilegroupLoad',
    'FilegroupNetCDF'
]
