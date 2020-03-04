"""Objects for indexing the data array."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


import logging
from typing import List

import numpy as np


log = logging.getLogger(__name__)


class Key():
    """Element for indexing a dimension of an array.

    Can be None, int, List[int] or slice.

    See :doc:`../accessor` for more information.

    Parameters
    ----------
    key: None, int, List[int], slice
        Key-like object.

    Attributes
    ----------
    value: None, int, List[int], slice
    type: str
        {'none', 'int', 'list', 'slice'}
    """

    int_types = (int, np.integer)

    def __init__(self, key):
        reject = False
        if isinstance(key, (list, tuple, np.ndarray)):
            reject = not all(isinstance(z, self.int_types) for z in key)
            tp = 'list'
            key = [int(z) for z in key]
        elif isinstance(key, self.int_types):
            tp = 'int'
            key = int(key)
        elif isinstance(key, slice):
            tp = 'slice'
        elif key is None:
            tp = 'none'
        else:
            reject = True
        if reject:
            raise TypeError("Key is not int, List[int], or slice"
                            " (is %s)" % type(key))
        self.value = key
        self.type = tp
        self.shape = None
        self.set_shape()

    def __eq__(self, other):
        return self.value == other.value

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return '\n'.join([super().__repr__(), str(self)])

    def copy(self) -> "Key":
        """Return copy of self."""
        if self.type == 'list':
            value = self.value.copy()
        else:
            value = self.value
        key = Key(value)
        key.shape = self.shape
        key.parent_shape = self.parent_shape
        return key

    def set_shape(self):
        """Set shape if possible.

        Shape is the size an array would have
        if the key was applied.

        Is None if cannot be determined from
        the key alone.
        """
        if self.type == 'int':
            self.shape = 0
        elif self.type == 'list':
            self.shape = len(self.value)
        else:
            self.shape = None
        self.parent_shape = None

    def set_shape_coord(self, coord):
        """Set shape using a coordinate.

        Parameters
        ----------
        coord: Coord
            The coordinate that would be used.
        """
        self.shape = coord[self.value].size
        self.parent_shape = coord.size

    def no_int(self):
        """Return value, replaces int with list.

        Returns
        -------
        value: key-like
        """
        if self.type == 'int':
            return [self.value]
        return self.value

    def reverse(self, size):
        """Reverse key.

        Parameters
        ----------
        size: int
            Size of the coordinate.
        """
        if self.type == 'int':
            self.value = size - self.value
        elif self.type == 'list':
            self.value = [size - z for z in self.value]
        elif self.type == 'slice':
            self.value = reverse_slice(self.value, size)

    def simplify(self):
        """Simplify list into a list.

        Transform a list into a slice if the list is
        a serie of integers of fixed step.
        """
        if self.type == 'list':
            key = list2slice_simple(self.value)
            if isinstance(key, slice):
                self.type = 'slice'
            self.value = key

    def tolist(self):
        """Transform key into list."""
        a = self.value
        if self.type == 'int':
            a = [a]
        elif self.type == 'list':
            a = a.copy()
        elif self.type == 'slice':
            if self.parent_shape is None:
                raise TypeError("%s has not had its parent shape specified." % self.value)
            a = list(range(*self.value.indices(self.parent_shape)))
        return a

    def __mul__(self, other):
        """Subset key by another.

        If `B = A[self]`
        and `C = B[other]`
        then `C = A[self*other]`

        The type of the resulting key is of the strongest
        type of the two keys (int > list > slice).

        Parameters
        ----------
        other: Key

        Returns
        -------
        Key
            self*other
        """
        a = self.value
        if self.type == 'int':
            a = [a]
        elif self.type == 'slice':
            if self.parent_shape is None:
                raise TypeError("%s has not had its parent shape specified." % self.value)
            a = list(range(*self.value.indices(self.parent_shape)))

        key = other.value
        if other.type == 'int':
            key = [key]
        if other.type == 'slice':
            res = a[key]
        else:
            res = [a[k] for k in key]

        if self.type == 'int' or other.type == 'int':
            return Key(int(res[0]))
        if self.type == 'list' or other.type == 'list':
            return Key(list(res))
        res_slc = Key(list2slice_simple(res))
        res_slc.shape = len(res)
        res_slc.parent_shape = self.parent_shape
        return res_slc

    def __add__(self, other):
        """Expand a key by another.

        If `B = A[self]` and `C=A[other]`
        concatenate(B, C) = A[self + other]

        The type of the resulting key is a list,
        or a slice if one of the argument is a slice
        and the result can be written as one.

        Parameters
        ----------
        other: Key

        Returns
        -------
        Key
            self + other
        """
        a = self.tolist()
        b = other.tolist()
        key = a + b

        if self.type == 'slice' or other.type == 'slice':
            key = list2slice_simple(key)

        return Key(key)

    def sort(self):
        if self.type == 'list':
            self.value = list(set(self.value))
            self.value.sort()


class Keyring():
    """Object for indexing an array.

    Multiple dimensions can be specified.

    See :doc:`../accessor` for more information.

    Parameters
    ----------
    keys: Key-like
        What part of the data must be selected
        for a given dimension.
    """

    @classmethod
    def get_default(cls, keyring=None, **keys) -> "Keyring":
        """Return a new keyring, eventually updated.

        Parameters
        ----------
        keyring: Keyring, optional
            Keyring to take values from.
        keys: Key, Key-like
            Keys to add to the keyring.
        """
        if keyring is None:
            keyring = cls()
        else:
            keyring = keyring.copy()
        keyring.update(keys)
        return keyring

    def __init__(self, **keys):
        self._keys = {}

        for name, key in keys.items():
            self[name] = key

    def __getitem__(self, item) -> Key:
        """Return key for a dimension.

        Parameters
        ----------
        item: str
            Dimension name.
        """
        return self._keys[item]

    def __setitem__(self, item, value):
        """Set key value to dimension.

        Parameters
        ----------
        item: str
            Dimension name
        value: Key, key-like
        """
        if not isinstance(value, Key):
            value = Key(value)
        self._keys[item] = value

    def __iter__(self):
        """Returns dict iterator over dimensions names."""
        return iter(self._keys)

    def __len__(self) -> int:
        """Returns number of dimensions."""
        return len(self._keys)

    @property
    def dims(self) -> List[str]:
        """List of dimensions present in the keyring."""
        return list(self._keys.keys())

    @property
    def keys(self) -> List[Key]:
        """List of keys present in the keyring."""
        return list(self._keys.values())

    @property
    def keys_values(self):
        """List of keys values present in the keyring.

        Returns
        -------
        List[Key-like]
        """
        return [k.value for k in self.keys]

    @property
    def kw(self):
        """Return dictionary of keys values.

        Returns
        -------
        Dict[str, Key-like]
        """
        return dict(zip(self.dims, self.keys_values))

    @property
    def shape(self) -> List[int]:
        """Return shape of all keys."""
        return [k.shape for k in self.keys]

    def __bool__(self):
        """If the keyring has keys."""
        return len(self.dims) > 0

    def subset(self, dims):
        """Return a subpart of this keyring.

        Parameters
        ----------
        dims: List[str]

        Returns
        -------
        Keyring
             Keyring with only specified keys.
        """
        return Keyring(**{c: self[c] for c in dims})

    def items(self):
        """Iterate through dimensions and keys.

        Returns
        -------
        Dict_item(List[str], List[Key])
        """
        return self._keys.items()

    def items_values(self):
        """List of keys values present in the keyring.

        Returns
        -------
        Dict_item(List[str], List[key-like]])
        """
        d = {name: key.value for name, key in self.items()}
        return d.items()

    def update(self, keys):
        """Update keyring.

        Parameters
        ----------
        keys: Dict[Key or key-like]
        """
        for name, key in keys.items():
            self[name] = key

    def pop(self, dim: str) -> Key:
        """Pop a key."""
        return self._keys.pop(dim)

    def __str__(self):
        s = []
        for c, key in self.items():
            s.append('%s: %s' % (c, str(key)))
        return str(', '.join(s))

    def __repr__(self):
        return '\n'.join([super().__repr__(), str(self)])

    def copy(self) -> "Keyring":
        """Return copy of self."""
        args = {c: k.copy() for c, k in self.items()}
        return Keyring(**args)

    def set_shape(self, coords):
        """Set shape of all keys using coordinates.

        Parameters
        ----------
        coords: Dict[Coord]
        """
        for name, c in coords.items():
            self[name].set_shape_coord(c)

    def get_non_zeros(self) -> List[str]:
        """Return dimensions name with a non zero shape.

        ie whose dimension would not be squeezed.
        """
        return [name for name, k in self.items()
                if k.shape is None or k.shape > 0]

    def sort_by(self, order):
        """Sort keys by order.

        Parameters
        ----------
        order: List[str]
             Dimensions present in the keyring.
        """
        if len(order) < len(self.keys):
            raise IndexError("Order given is too short.")

        keys_ord = {}
        for name in order:
            keys_ord[name] = self[name]
        self._keys = keys_ord

    def check_unwanted(self, dims):
        """Check if keyring contains unwanted dimensions."""
        for c in self:
            if c not in dims:
                raise KeyError("'%s' dimension is unwanted in keyring." % c)

    def make_full(self, dims, fill=None):
        """Add dimensions.

        Parameters
        ----------
        dimensions: List[str]
            List of dimensions to add if not
            already present.
        fill: Any, optional
            Value to set new keys to.
        """
        for c in self:
            if c not in dims:
                log.warning("'%s' dimension in keyring is not in specified "
                            "full list of dimensions, and might be unwanted.", c)
        for c in dims:
            if c not in self:
                self[c] = fill

    def make_total(self, *dims, miss=None):
        """Fill missing keys by total slices.

        Parameters
        ----------
        dims: str, optional
            Dimensions names to fill if missing.
            If not specified, all are selected.
        miss: Any, optional
            Value of the key to flag as missing.
        """
        if not dims:
            dims = self.dims
        for c, v in self.items_values():
            if c in dims and v == miss:
                self[c] = slice(None, None)

    def make_single(self, *dims, idx=0, miss=None):
        """Fill missing keys by an index.

        Parameters
        ----------
        dims: str, optional
            Dimensions names to fill if missing.
            If not specified, all are selected.
        idx: int, optional
            Index to set as value.
        miss: Any
            Value of the key to flag as missing.
        """
        if not dims:
            dims = self.dims
        for c, v in self.items_values():
            if c in dims and v == miss:
                self[c] = idx

    def make_int_list(self, *dims):
        """Turn integer values into lists.

        Parameters
        ----------
        dims: str
             Dimensions names to change if
             necessary. If not specified, all are
             selected.
        """
        if not dims:
            dims = self.dims
        for c, k in self.items():
            if c in dims and k.type == 'int':
                self[c] = [k.value]

    def get_high_dim(self) -> List[str]:
        """Returns coordinates of size higher than one."""
        out = [c for c, k in self.items()
               if k.shape is None or k.shape > 1]
        return out

    def simplify(self):
        """Simplify keys.

        Turn list into a slice if possible.
        """
        for key in self.keys:
            key.simplify()

    def sort_keys(self, *dims):
        """Sort keys.

        Remove redondant indices.
        Sort by indices.
        """
        if dims is None:
            dims = self.dims
        for d in dims:
            d.sort()

    def __mul__(self, other):
        """Subset keyring by another.

        If `B = A[self]`
        and `C = B[other]`
        then `C = A[self*other]`

        Parameters
        ----------
        other: Keyring

        Returns
        -------
        Keyring
            self*other
        """
        res = Keyring()
        other_ = other.copy()
        other_.make_full(self.dims)
        other_.make_total()
        for name, key in self.items():
            res[name] = key * other_[name]
        return res


def list2slice_simple(L):
    """Transform a list into a slice when possible.

    Step can be any integer.
    Can be descending.
    """
    if len(L) < 2:
        return L

    diff = np.diff(L)
    if len(L) == 2:
        diff2 = np.array([0])
    else:
        diff2 = np.diff(diff)

    if np.all(diff2 == 0):
        step = diff[0]
        start = L[0]
        stop = L[-1] + step

        if stop < 0:
            stop = None
        L = slice(start, stop, step)

    return L


def list2slice_complex(L):
    """Transform a list of integer into a list of slices.

    Find all series of continuous integer with a fixed
    step (that can be any integer) of length greater than 3.

    Examples
    --------
    [0, 1, 2, 3, 7, 8, 9, 10, 16, 14, 12, 10, 3, 10, 11, 12]
    will yield:
    [slice(0, 4, 1), slice(8, 11, 1), slice(16, 9, -2), 3, slice(10, 13, 1)]
    """
    if len(L) < 3:
        return L

    diff = list(np.diff(L))
    diff2 = np.diff(diff)

    # Index of separation between two linear parts
    sep = np.where(diff2 != 0)[0]
    # Only one of the index (this is a second derivative of a step function)
    sep_start = sep[np.where(np.diff(sep) == 1)[0]] + 2

    idx = list(sep_start)
    if diff[0] != diff[1]:
        idx.insert(0, 1)
    if diff[-1] != diff[-2]:
        idx.append(len(L)-1)
        diff.append(diff[-1]+1)

    idx.insert(0, 0)
    idx.append(len(L))

    slices = []
    for i in range(len(idx)-1):
        i1 = idx[i]
        i2 = idx[i+1]
        start = L[i1]

        if i2 - i1 == 1:
            slices.append([start])
            continue

        step = diff[i1]
        stop = L[i2-1] + 1

        if step < 0:
            stop -= 2
            if stop == -1:
                stop = None

        slc = slice(start, stop, step)
        slices.append(slc)

    return slices


def simplify_key(key):
    """Simplify a key.

    Transform a list into a slice if the list is
    a serie of integers of fixed step.
    """
    if isinstance(key, (list, tuple, np.ndarray)):
        key = list2slice_simple(list(key))
    return key


def reverse_slice(sl, size=None):
    """Reverse a slice.

    Parameters
    ----------
    sl: Slice
        Slice to reverse.
    size: int, optional
        Size of the list to get indices from.
    """
    if size is None:
        size = sl.stop - sl.start

    ind = sl.indices(size)
    shift = [-1, 1][ind[2] < 0]

    start = ind[1] + shift
    stop = ind[0] + shift
    step = -ind[2]

    if stop == -1:
        stop = None

    return slice(start, stop, step)
