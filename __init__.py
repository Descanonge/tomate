"""Manages sets of data on disk.

Manages:
-placement of data on disk
-loading of subset of this data
-variables and their metadata

This modules provides

VariableInfo:
    Holds metadata about variables

Data:
    Manages data
    Stores info on variables, coordinates, files on disk.
    Load the data.
    Once loaded store the data.
Package and Data class aimed at managing netCDF files for
oceanography purposes. But the abstract DataBase can be subclassed.

Files:
    Holds information of placement of files on disk, and in
    what variable group they hold.
VarGroup:
    Group of variable present in the same file.

Time:
    Tuple storing timestamps with some additional functionalities.

IterDict:
    dictionnary which can be indexed. Order of items
    is preserved (in python 3.7)
"""


from .iterDict import IterDict
from .data import Data
from .files import Files, VarGroup
from .time import Time
from .variablesInfo import VariablesInfo


__all__ = ['IterDict', 'Data', 'Files', 'VarGroup', 'Time', 'VariablesInfo']
