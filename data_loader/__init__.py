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

from .log import set_logging

from .coord import Coord
from .time import Time
from .iter_dict import IterDict
from .variables_info import VariablesInfo


__version__ = "0.2"

__all__ = [
    'Coord',
    'Time',
    'IterDict',
    'VariablesInfo',
]

set_logging()
