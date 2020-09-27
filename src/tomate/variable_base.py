"""Variable object."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK

import logging
from typing import Any, Iterable, List, Optional, TYPE_CHECKING, Union

import numpy as np

from tomate.accessor import Accessor
from tomate.custom_types import Array, KeyLike, KeyLikeValue
from tomate.keys.key import Key
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

    :attr name: str: Variable name.
    :attr _db: DataBase: DataBase instance.
    :attr data: Array: Variable data.
    :attr dims: List[str]: List of dimensions the variable
        depends on.
    :attr datatype: Any: Type of data used to allocate array. Passed to
        accessor.allocate. Can be string that can be turned in numpy.dtype.
    """

    acs = Accessor  #: Accessor class (or subclass) to use to access the data.

    __array_priority__ = 2  #: So Numpy let me use reflective operators

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

    @property
    def attributes(self) -> VariableAttributes:
        """Attributes for this variable.

        Returns a 'VariableAttributes' that is tied to the parent database VI.
        """
        return self._db.vi[self.name]

    @property
    def shape(self) -> List[int]:
        """Variable shape for current scope."""
        scope = self._db.scope
        return [scope[d].size for d in self.dims]

    def __repr__(self):
        s = [str(self),
             "Dimensions: {}".format(self.dims),
             "Datatype: {}".format(self.datatype)]
        if self.is_loaded():
            s.append("Loaded (shape: {})".format(self.shape))
        return '\n'.join(s)

    def __str__(self):
        return "{}: {}".format(self.__class__.__name__, self.name)

    def __getitem__(self, key) -> Array:
        """Access data array directly."""
        if self.data is None:
            raise AttributeError(f"Data not loaded for {self.name}")
        return self.data[key]

    def __setitem__(self, key, value):
        """Access data array directly."""
        if self.data is None:
            raise AttributeError(f"Data not loaded for {self.name}")
        self.data[key] = value

    def allocate(self, shape: Iterable[int] = None):
        """Allocate data of given shape.

        :param shape: If None, shape is determined from loaded scope.
        """
        if shape is None:
            shape = [self._db.loaded.dims[d].size
                     for d in self.dims]
        log.info("Allocating %s of type %s for %s",
                 shape, self.datatype, self.name)
        self.data = self.acs.allocate(shape, datatype=self.datatype)

    def unload(self):
        """Unload data.

        Set data to None, and remove variable from loaded scope.
        """
        if self.name in self._db.loaded:
            self._db.remove_loaded_variables(self.name)
        self.data = None

    def view(self, *keys: KeyLike, keyring: Keyring = None,
             order: List[str] = None, log_lvl: str = 'DEBUG',
             **kw_keys: KeyLike,) -> Optional[Array]:
        """Return subset of data.

        See also
        --------
        tomate.data_base.DataBase.view for details on arguments.
        """
        if not self.is_loaded():
            return None

        kw_keys = self._db.get_kw_keys(*keys, **kw_keys)
        keyring = Keyring.get_default(keyring=keyring, **kw_keys)
        keyring.make_full(self.dims)
        keyring.make_total()
        keyring = keyring.subset(self.dims)
        keyring.make_str_idx(**self._db.loaded.dims)

        if log_lvl:
            log.log(getattr(logging, log_lvl.upper()),
                    'Taking keys from %s: %s', self.name, keyring.print())
        out = self.acs.take(keyring, self.data)
        if order is not None:
            out = self.acs.reorder(keyring.get_non_zeros(), out,
                                   order, log_lvl=log_lvl)

        return out

    def view_by_value(self, *keys: KeyLikeValue,
                      by_day: bool = False, order: List[str] = None,
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
        keyring = self._db.loaded.get_keyring_by_index(by_day=by_day, **kw_keys)
        return self.view(keyring=keyring, order=order)

    def set_data(self, array: Array, keyring: Keyring = None, **keys: KeyLike):
        """Set subset of data.

        If no data is loaded, loaded scope is set from the `keys` which then act
        on the available scope.

        Otherwise use `array` to set a part of this variable, `keys` then
        specify the part of loaded scope to set. If this variable is not loaded
        (but others are), allocate this variable first.

        :param array: Data Array. Its shape should correspond to the keys.
        """
        keyring = Keyring.get_default(keyring, **keys)
        keyring.make_full(self.dims)
        keyring = keyring.subset(self.dims)
        keyring.make_total()

        if self._db.loaded.is_empty():
            self._db.loaded = self._db.get_subscope('avail', keyring,
                                                    name='loaded',
                                                    var=self.name)
        if not self.is_loaded():
            self.allocate()
        if self.name not in self._db.loaded.var:
            self._db.loaded.var.append(self.name)
            key = self._db.avail.var.get_str_index(self.name)
            self._db.loaded.parent_keyring['var'] += Key(key)

        keyring.make_str_idx(**self._db.loaded.dims)
        self.acs.place(keyring, self.data, array)

    def set_attribute(self, name: str, value: Any):
        """Set variable specific attribute to VI."""
        self.attributes[name] = value

    def is_loaded(self) -> bool:
        """If data is loaded."""
        return self.data is not None

    def check_loaded(self):
        """Raises if data is loaded.

        :raises RuntimeError: If the data is not loaded.
        """
        if not self.is_loaded():
            raise RuntimeError("Data not loaded.")

    def _apply_op(self, op, other):
        self.check_loaded()

        if isinstance(other, (Variable, np.ndarray)):
            if isinstance(other, Variable):
                var = other.name
                shape_other = other.shape
            else:
                var = 'array'
                shape_other = self.acs.shape(other)
            shape = self.shape

            if len(shape) == len(shape_other):
                k_self = tuple([slice(None)]*len(shape))
                k_other = tuple([slice(None)]*len(shape))
            elif len(shape) > len(shape_other):
                k_self = tuple([slice(None)]*len(shape))
                k_other = find_broadcasting_keys(shape, shape_other)
                log.info('Broadcasting %s to %s', var, shape_other)
            else:
                k_self = find_broadcasting_keys(shape_other, shape)
                k_other = tuple([slice(None)]*len(shape_other))
                log.info('Broadcasting %s to %s', self.name, shape)

            a = self.data[k_self]
            b = other[k_other]
        else:
            a, b = self.data, other

        f = getattr(a, f'__{op}__')
        return f(b)

    def __add__(self, other: Union['Variable', Array]):
        return self._apply_op('add', other)

    def __sub__(self, other: Union['Variable', Array]):
        return self._apply_op('sub', other)

    def __mul__(self, other: Union['Variable', Array]):
        return self._apply_op('mul', other)

    def __truediv__(self, other: Union['Variable', Array]):
        return self._apply_op('truediv', other)

    def __mod__(self, other: Union['Variable', Array]):
        return self._apply_op('mod', other)

    def __and__(self, other: Union['Variable', Array]):
        return self._apply_op('and', other)

    def __or__(self, other: Union['Variable', Array]):
        return self._apply_op('or', other)

    def __xor__(self, other: Union['Variable', Array]):
        return self._apply_op('xor', other)

    def __radd__(self, other: Union['Variable', Array]):
        return self + other

    def __rsub__(self, other: Union['Variable', Array]):
        return self - other

    def __rmul__(self, other: Union['Variable', Array]):
        return self * other

    def __rtruediv__(self, other: Union['Variable', Array]):
        return self / other

    def __rmod__(self, other: Union['Variable', Array]):
        return self % other

    def __rand__(self, other: Union['Variable', Array]):
        return self & other

    def __ror__(self, other: Union['Variable', Array]):
        return self | other

    def __rxor__(self, other: Union['Variable', Array]):
        return self ^ other

    def __pow__(self, value: Union[int, float]):
        return self.data ** value

    def __pos__(self):
        return self.data

    def __neg__(self):
        return -self.data


def find_broadcasting_keys(shape1, shape2):
    keys = []
    for i, s1 in enumerate(shape1):
        if i >= len(shape2) or s1 != shape2[i]:
            if len(shape1) == len(shape2):
                raise IndexError("Incompatible arrays")
            shape2.insert(i, None)
            keys.append(np.newaxis)
        else:
            keys.append(slice(None))

    return tuple(keys)
