"""Variable object."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK

from typing import List, TYPE_CHECKING

from tomate.accessor import Accessor
from tomate.custom_types import Array
from tomate.keys.keyring import Keyring

if TYPE_CHECKING:
    from tomate import DataBase


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
                 data: Array = None,
                 database: 'DataBase' = None):
        self.name = name
        self.db = database

        if len(self.acs.shape(data)) != len(dims):
            raise IndexError("Data has incompatible shape for provided"
                             " dimensions. (shape: {}, dimensions: {})"
                             .format(self.acs.shape(data), dims))
        self._data = data
        self.dims = dims
        self.datatype = self.acs.get_datatype(data)

    def __repr__(self):
        s = "Variable: {}".format(self.name)
        return s

    def __getitem__(self, key) -> Array:
        return self._data[key]

    def view(self, keyring=None, **keys):
        keyring = Keyring.get_default(keyring=keyring, **keys)
        keyring = keyring.subset(self.dims)
        out = self.acs.take(self._data, keyring)
        return out

    def set_data(self, chunk, keyring: Keyring = None):
        keyring.make_full(self.dims)
        keyring.make_total()
        self.acs.place(keyring, self.data, chunk)
