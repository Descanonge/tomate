"""Collection of DataBase subclasses."""


import importlib

from .data_compute import DataCompute
from .masked.data_masked import DataMasked
from .data_disk import DataDisk

__all__ = [
    'DataCompute',
    'DataMasked',
    'DataDisk'
]

if importlib.util.find_spec('matplotlib') is not None:
    from .plotting.data_plot import DataPlot
    __all__.append('DataPlot')
