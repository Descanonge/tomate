"""Variable object."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK

from typing import Iterable, List, TYPE_CHECKING

from tomate.accessor import Accessor
from tomate.custom_types import Array, KeyLikeVar
from tomate.keys.keyring import Keyring

if TYPE_CHECKING:
    from tomate import DataBase


class VariableSpec:
    def __init__(self, name: str,
                 in_idx: KeyLikeVar = '__equal_as_name__',
                 dims: List[str] = None):
        if in_idx == '__equal_as_name__':
            in_idx = name
        self.name = name
        self.in_idx = in_idx
        self.dims = dims


class Variable():
    """Holds data for a single variable.

    :param name: Variable name.
    :param dims: List of dimensions the variable depends on,
        in order.
    :param data: Variable data.
    :param database: DataBase instance this variable belongs to.
    """

    acs = Accessor  #: Accessor class (or subclass) to use to access the data.

    def __init__(self, name: str,
                 dims: List[str],
                 database: 'DataBase',
                 data: Array = None):

        self.name = name
        self._db = database

        self.data = None
        self.dims = dims
        self.datatype = None

        if data is not None:
            self.set_data(data)
            self.datatype = self.acs.get_datatype(data)

    def __repr__(self):
        s = "Variable: {}".format(self.name)
        return s

    def __getitem__(self, key) -> Array:
        if self.data is None:
            raise AttributeError(f"Data not loaded for {self.name}")
        return self.data[key]

    def allocate(self, shape: Iterable[int] = None):
        if shape is None:
            shape = [self._db.loaded.dims[d].size
                     for d in self.dims]
        self.data = self.acs.allocate(shape)

    def view(self, keyring=None, **keys):
        keyring = Keyring.get_default(keyring=keyring, **keys)
        keyring = keyring.subset(self.dims)
        out = self.acs.take(self.data, keyring)
        return out

    def set_data(self, chunk, keyring: Keyring = None):
        keyring.make_full(self.dims)
        keyring.make_total()
        self.acs.place(keyring, self.data, chunk)
