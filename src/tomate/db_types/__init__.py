"""Collection of DataBase subclasses."""


import importlib.util

from .data_compute import DataCompute
from .data_disk import DataDisk

__all__ = [
    'DataCompute',
    'DataDisk'
]

if importlib.util.find_spec('matplotlib') is not None:
    from .plotting.data_plot import DataPlot  # noqa: F401
    __all__.append('DataPlot')
