"""Variable object."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK

import logging
from typing import Any, Iterable, List, TYPE_CHECKING

from tomate.accessor import Accessor
from tomate.custom_types import Array, KeyLike, KeyLikeValue
from tomate.keys.keyring import Keyring
from tomate.variables_info import VariableAttributes

if TYPE_CHECKING:
    from tomate import DataBase


log = logging.getLogger(__name__)


class Variable():
    """Holds data for a single variable.

    :param name: Variable name.
    :param dims: List of dimensions the variable depends on,
        in order.
    :param database: DataBase instance this variable belongs to.
    :param data: [opt] Variable data.

    :attr name: str: Variable name
    :attr data: Array: Variable data.
    :attr dims: List[str]: List of dimensions the variable
        depends on.
    :attr datatype: Any: Type of data used to allocate array.
        Can be string that can be turned in numpy.dtype.
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
        s = [str(self),
             "Dimensions: {}".format(self.dims),
             "Type: {}".format(self.datatype)]
        if self.is_loaded():
            s.append("Loaded (shape: {})".format(self.shape))
        return '\n'.join(s)

    def __str__(self):
        return "{}: {}".format(self.__class__.__name__, self.name)

    def __getitem__(self, key) -> Array:
        """Get data subset."""
        if self.data is None:
            raise AttributeError(f"Data not loaded for {self.name}")
        return self.data[key]

    @property
    def attrs(self) -> VariableAttributes:
        """Attributes for this variable.

        Returns a 'VariableAttributes' that is tied to
        the parent database VI.
        """
        return self._db.vi[self.name]

    @property
    def shape(self) -> List[int]:
        """Variable shape for current scope."""
        scope = self._db.scope
        return [scope[d].size for d in self.dims]

    def allocate(self, shape: Iterable[int] = None):
        """Allocate data of given shape.

        :param shape: If None, shape is determined from
            loaded scope.
        """
        if shape is None:
            shape = [self._db.loaded.dims[d].size
                     for d in self.dims]
        self.data = self.acs.allocate(shape, datatype=self.datatype)

    def view(self, *keys: KeyLike, keyring: Keyring = None,
             order: List[str] = None, **kw_keys: KeyLike) -> Array:
        """Return subset of data.

        See also
        --------
        tomate.data_base.DataBase.view for details on arguments.
        """
        kw_keys = self._db.get_kw_keys(*keys, **kw_keys)
        keyring = Keyring.get_default(keyring=keyring, **kw_keys)
        keyring.make_full(self.dims)
        keyring.make_total()
        keyring = keyring.subset(self.dims)

        log.debug('Taking keys from %s: %s', self.name, keyring.print())
        out = self.acs.take(keyring, self.data)
        if order is not None:
            out = self.acs.reorder(keyring.get_non_zeros(), out, order)

        return out

    def view_by_value(self, *keys: KeyLikeValue,
                      by_day: bool = False,
                      order: List[str] = None,
                      **kw_keys: KeyLikeValue) -> Array:
        """Returns a subset of loaded data.

        Arguments work similarly as
        :func:`DataDisk.load_by_value
        <tomate.db_types.data_disk.DataDisk.load_by_value>`.

        See also
        --------
        view
        """
        self.check_loaded()
        kw_keys = self._db.get_kw_keys(*keys, **kw_keys)
        keyring = self.loaded.get_keyring_by_index(by_day=by_day, **kw_keys)
        return self.view(keyring=keyring, order=order)

    def set_data(self, chunk: Array, keyring: Keyring):
        """Set subset of data."""
        keyring.make_full(self.dims)
        keyring.make_total()
        self.acs.place(keyring, self.data, chunk)

    def get_attr(self, key: str, default: Any = None):
        """Get variable specific attribute from VI."""
        return self.attrs.get(key, default)

    def set_attr(self, name: str, value: Any):
        """Set variable specific attribute to VI."""
        self.attrs[name] = value

    def is_loaded(self) -> bool:
        """If data is loaded."""
        return self.data is not None
