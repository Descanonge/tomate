"""Manages sets of data on disk.

Manages

* placement of data on disk
* loading of subsets of this data
* variables and their metadata
"""

import sys

from .log import set_logging

from .coordinates.coord import Coord
from .coordinates.time import Time
from .coordinates.latlon import Lat, Lon

from .key import Keyring

from .iter_dict import IterDict
from .variables_info import VariablesInfo
from .data_base import DataBase
from .constructor import Constructor


__version__ = "0.2"

__all__ = [
    'Coord',
    'Time',
    'Lat',
    'Lon',
    'Keyring',
    'IterDict',
    'VariablesInfo',
    'DataBase',
    'Constructor'
]


if sys.version_info[:2] < (3, 7):
    raise Exception("Python 3.7 or above is required.")


set_logging()
