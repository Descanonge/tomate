"""Variable object."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK

from typing import Iterable, List, TYPE_CHECKING

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
        s = ["{}: {}".format(self.__class__.__name__, self.name),
             "Dimensions: {}".format(self.dims),
             "Type: {}".format(self.datatype)]
        if self.is_loaded():
            s.append("Loaded (shape: {})".format(self.acs.shape(self.data)))
        return '\n'.join(s)

    def __str__(self):
        return "{}: {}".format(self.__class__.__name__, self.name)

    def __getitem__(self, key) -> Array:
        if self.data is None:
            raise AttributeError(f"Data not loaded for {self.name}")
        return self.data[key]

    @property
    def attrs(self):
        """Attributes for this variable."""
        return self._db.vi[self.name]

    def allocate(self, shape: Iterable[int] = None):
        if shape is None:
            shape = [self._db.loaded.dims[d].size
                     for d in self.dims]
        self.data = self.acs.allocate(shape, datatype=self.datatype)

    def view(self, keyring=None, **keys):
        keyring = Keyring.get_default(keyring=keyring, **keys)
        keyring = keyring.subset(self.dims)
        out = self.acs.take(keyring, self.data)
        return out

    def set_data(self, chunk, keyring: Keyring = None):
        keyring.make_full(self.dims)
        keyring.make_total()
        self.acs.place(keyring, self.data, chunk)

    def get_attr(self, key, default=None):
        return self.attrs.get(key, default)

    def set_attr(self, name, value):
        self.attrs[name] = value

    def is_loaded(self):
        return self.data is not None
