"""Manages sets of data on disk.

Manages:

    -placement of data on disk
    -loading of subsets of this data
    -variables and their metadata


Contains
--------

VariablesInfo
    Holds metadata on variables.

DataBase
    Stores info on variables, coordinates, files on disk.
    Load the data.
    Once loaded store the data.
    Can be subclassed for additional features.

Filegroup
    Holds information on a grouping of files sharing the
    same arrangement on disk, same filename construction,
    and the same variables.
    Manages scanning of files.
    FilegroupLoad is to be subclassed for each file-format.

Constructor
    Help to create a database.

Coord
    Coordinates (ie dimensions) for the data.
Time
    Coord with additional functionalities for handling
    dates.
CoordScan
    Coord for scanning files on disk.

IterDict
    Dictionnary which can be indexed. Order of items
    is preserved (in python 3.7+).
"""

from .log import set_logging

from .coord import Coord
from .time import Time
from .iter_dict import IterDict
from .variables_info import VariablesInfo
from .data_base import DataBase
from .constructor import Constructor


__version__ = "0.2"

__all__ = [
    'Coord',
    'Time',
    'IterDict',
    'VariablesInfo',
    'DataBase',
    'Constructor'
]

set_logging()
