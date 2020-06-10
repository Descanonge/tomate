"""Manages sets of data on disk.

Tomate provides ways to manipulate data under the form of a
multi-dimensional array.
It manages multiples variables, as well as the coordinates along
which the data varies.
It also provides multiple convenience functions to retrieve
subpart of the data, do computations, or plot the data.

The data can be retrieved from disk, where it can be arranged
in multiple ways and formats.
Information on the data, such as variable attributes,
or coordinates values can be retrieved automatically.
"""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import sys

import tomate.log

from .coordinates.coord import Coord
from .coordinates.time import Time
from .coordinates.latlon import Lat, Lon
from .coordinates.variables import Variables

from .keys.keyring import Keyring

from .variables_info import VariablesInfo
from .data_base import DataBase
from .constructor import Constructor


__version__ = "1.0.0"


__all__ = [
    'Coord',
    'Time',
    'Lat',
    'Lon',
    'Variables',

    'Keyring',

    'VariablesInfo',
    'DataBase',
    'Constructor'
]


if sys.version_info[:2] < (3, 7):
    raise Exception("Python 3.7 or above is required.")


tomate.log.set_logging_defaults()
