"""Manages sets of data on disk.

Manages:
-placement of data on disk
-loading of subsets of this data
-variables and their metadata


Contains
--------

VariablesInfo:
    Holds metadata on variables

Data:
    Stores info on variables, coordinates, files on disk.
    Load the data.
    Once loaded store the data.
An abstract class (_DataBase) can be subclassed for different
types or arrangements of files.
DataNetCDF is such an implementation for NetCDF files.

Filegroup:
    Holds information on a grouping of files sharing the
    same arrangement on disk, same filename construction,
    and the same variables.
    Manages scanning of files.

Coord:
    Coordinates (ie dimensions) for the data.
Time:
    Coord with additional functionalities for handling
    dates.
CoordScan:
    Coord for scanning files on disk.

IterDict:
    dictionnary which can be indexed. Order of items
    is preserved (in python 3.7+)
"""


from data_loader.coord import Coord
from data_loader.iter_dict import IterDict
from data_loader.data_netcdf import DataNetCDF
from data_loader.filegroup import Filegroup
from data_loader.time import Time
from data_loader.variables_info import VariablesInfo


__all__ = ['Coord',
           'IterDict',
           'DataNetCDF',
           'Filegroup',
           'Time',
           'VariablesInfo']
