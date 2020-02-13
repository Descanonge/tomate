"""Module compiling filegroups type."""


from .filegroup_load import FilegroupLoad
from .filegroup_netcdf import FilegroupNetCDF

__all__ = [
    'FilegroupLoad',
    'FilegroupNetCDF'
]
