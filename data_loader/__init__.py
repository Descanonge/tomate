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

import logging

from data_loader.coord import Coord
from data_loader.time import Time
from data_loader.iter_dict import IterDict
from data_loader.variables_info import VariablesInfo
from data_loader.filegroup import Filegroup


__version__ = "0.2"

__all__ = [
    'Coord',
    'Time',
    'IterDict',
    'VariablesInfo',
    'Filegroup',
    'set_logging'
]


def set_logging(level='INFO'):
    """Set package-wide logging level."""
    level_num = getattr(logging, level.upper())
    logging.getLogger(__name__).setLevel(level_num)

logging.basicConfig()
set_logging()
