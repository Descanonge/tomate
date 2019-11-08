"""Module for loading NetCDF files."""

from data_loader.netcdf.data_netcdf import DataNetCDF
import data_loader.netcdf.mask as mask

__all__ = [
    'DataNetCDF',
    'mask'
]
