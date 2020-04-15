"""Keys for indexing arrays."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK

import numpy as np


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
    INT_TYPES: List[Type]
        Types that are considered integer.
    value: None, int, List[int], slice
    type: str
        {'none', 'int', 'list', 'slice'}
    """

    INT_TYPES = (int, np.integer)

    def __init__(self, key):
        self.value = None
        self.type = ''
        self.shape = None
        self.parent_size = None
        self.set(key)

    def set(self, key):
        """Set key value.

        Parameters
        ----------
        key: Key-like

        Raises
        ------
        TypeError
            If key is not a valid type.
        """
        reject = False
        if isinstance(key, (list, tuple, np.ndarray)):
            reject = any(not isinstance(z, self.INT_TYPES) for z in key)
            tp = 'list'
            key = [int(k) for k in key]
        elif isinstance(key, self.INT_TYPES):
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
        self.set_shape()

        if self.type == 'slice':
            self.make_slice_size(None)

    def __eq__(self, other):
        return self.value == other.value

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return '\n'.join([super().__repr__(), str(self)])

    def __iter__(self):
        """Iter through values."""
        try:
            val = self.tolist()
        except TypeError:
            val = [self.value]
        return iter(val)

    def make_slice_size(self, size=None):
        if size is None:
            size = get_slice_size(self.value)
        if size is not None:
            start, stop, step = self.value.start, self.value.stop, self.value.step
            if step is None or step > 0:
                if start is None:
                    start = 0
                if stop is None:
                    stop = size
                else:
                    stop = min(size, stop)
            else:
                if start is None:
                    start = size - 1
                else:
                    start = max(size-1, start)

            self.value = slice(start, stop, step)
            self.shape = len(list(range(*self.value.indices(size))))

    def copy(self) -> "Key":
        """Return copy of self."""
        if self.type == 'list':
            value = self.value.copy()
        else:
            value = self.value
        key = self.__class__(value)
        key.shape = self.shape
        key.parent_size = self.parent_size
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
        elif self.type == 'slice':
            self.shape = get_slice_size(self.value)
        elif self.type == 'none':
            self.shape = 0

    def set_shape_coord(self, coord):
        """Set shape using a coordinate.

        Parameters
        ----------
        coord: Coord
            The coordinate that would be used.
        """
        self.parent_size = coord.size
        if self.type == 'slice':
            self.make_slice_size(coord.size)

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
        size: int, optional
            Size of the coordinate.
            Default is the parent coordinate shape.
        """
        if self.type == 'int':
            self.value = size - self.value
        elif self.type == 'list':
            self.value = [size - z - 1 for z in self.value]
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
        """Transform key into list.

        Raises
        ------
        TypeError
            If key is slice an dhas not had its parent shape
            specified.
        """
        a = self.value
        if self.type == 'int':
            a = [a]
        elif self.type == 'list':
            a = a.copy()
        elif self.type == 'slice':
            if self.parent_size is not None:
                a = list(range(*self.value.indices(self.parent_size)))
        elif self.type == 'none':
            a = []
        return a

    def apply(self, seq):
        if self.type == 'int':
            return seq[self.value]
        if self.type == 'list':
            return [seq[i] for i in self.value]
        if self.type == 'slice':
            return seq[self.value]
        raise TypeError("Not appliable (key type '%s')." % self.type)

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
        a = self.tolist()
        key = other.value
        if other.type == 'int':
            key = [key]

        if other.type == 'slice':
            res = a[key]
        else:
            res = [a[k] for k in key]

        if self.type == 'int' or other.type == 'int':
            key = self.__class__(int(res[0]))
        elif self.type == 'list' or other.type == 'list':
            key = self.__class__(list(res))
        else:
            key = self.__class__(list2slice_simple(res))
            key.shape = len(res)
        return key

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

        return self.__class__(key)

    def sort(self):
        """Sort indices if in a list."""
        if self.type == 'list':
            self.value = list(set(self.value))
            self.value.sort()

    def make_list_int(self):
        """Make list of length one integer."""
        if self.type == 'list' and len(self.value) == 1:
            self.type = 'int'
            self.value = self.value[0]
            self.shape = 0

    def make_int_list(self):
        """Make integer a list of lenght one."""
        if self.type == 'int':
            self.type = 'list'
            self.value = [self.value]
            self.shape = 1


class KeyVar(Key):
    """Key for indexing Variable dimension.

    Add support for strings keys to Key.
    Allows to go from variable name to index (and
    vice-versa).

    Parameters
    ----------
    key: None, int, str, List[int], List[str], slice
        Key-like object.
        Can also be variable name, list of variables names, or
        a slice made from strings.

    Attributes
    ----------
    var: bool
        If the key-value can be used only for variables
        (*ie* it is or contains a string). In which case
        one can use `make_var_idx`.

    Examples
    --------
    Examples of values:
    >>> 0, [0, 1], 'sst', ['sst'], slice('sst', 'chl', 1)
    """

    def __init__(self, key):
        self.var = False
        super().__init__(key)

    def set(self, key):
        """Set value.

        Parameters
        ----------
        key: Key-like

        Raises
        ------
        TypeError
            Key is not of valid type.
        ValueError:
            Slice is not valid (step is not integer,
            or start and stop are not of the same type).
        """
        reject = False
        var = False
        if isinstance(key, str):
            tp = 'int'
            var = True
        elif isinstance(key, self.INT_TYPES):
            tp = 'int'
            key = int(key)
        elif isinstance(key, (list, tuple, np.ndarray)):
            if all([isinstance(k, str) for k in key]):
                tp = 'list'
                var = True
            elif all([isinstance(k, self.INT_TYPES) for k in key]):
                tp = 'list'
                key = [int(k) for k in key]
            else:
                reject = True
        elif isinstance(key, slice):
            tp = 'slice'
            slc = [key.start, key.stop, key.step]
            for i, s in enumerate(slc):
                if isinstance(s, self.INT_TYPES):
                    slc[i] = int(s)
            start, stop, step = slc
            invalid = False
            if step is not None and not isinstance(step, int):
                invalid = True
            types = {type(a) for a in [start, stop]
                     if a is not None}
            if types == set([str]):
                var = True
            if types not in (set([int]), set([str]), set()):
                invalid = True
            if invalid:
                raise ValueError("Invalid slice.")
        elif key is None:
            tp = 'none'
        else:
            reject = True

        if reject:
            raise TypeError("Key is not int, str, List[int], List[str] or slice"
                            " (is %s)" % type(key))
        self.value = key
        self.type = tp
        self.var = var
        self.set_shape()

    def reverse(self, size=None):
        if not self.var:
            super().reverse(size)

    def simplify(self):
        if not self.var:
            super().simplify()

    def tolist(self):
        if self.type == 'slice' and self.var:
            raise TypeError("Variable slice cannot be transformed into list.")
        return super().tolist()

    def tovarlist(self, variables):
        self.set(variables.get_var_names(self.value))

    def __mul__(self, other):
        if not other.var:
            return super().__mul__(other)
        if not self.var:
            raise TypeError("If other is var, self must be too.")

        a = self.tolist()
        key = other.value
        if other.type == 'int':
            key = [key]

        if other.type == 'slice':
            slc = slice(a.index(key.start), a.index(key.stop), key.step)
            res = a[slc]
        else:
            res = [z for z in a if z in key]

        if self.type == 'int' or other.type == 'int':
            key = KeyVar(res[0])
        elif self.type == 'list' or other.type == 'list':
            key = self.__class__(list(res))
        return key

    def make_idx_var(self, variables):
        """Transform indices into variables names.

        Parameters
        ----------
        variables: Variables
        """
        if not self.var:
            names = variables.get_var_names(self.value)
            self.set(names)
        self.set_shape_coord(variables)

    def make_var_idx(self, variables):
        """Transform variables names into indices.

        Parameters
        ----------
        variables: Variables
        """
        if self.var:
            idx = variables.get_var_indices(self.value)
            self.set(idx)
        self.set_shape_coord(variables)


def simplify_key(key):
    """Simplify a key.

    Transform a list into a slice if the list is
    a serie of integers of fixed step.
    """
    if isinstance(key, (list, tuple, np.ndarray)):
        key = list2slice_simple(list(key))
    return key

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


def get_slice_size(slc):
    size = None
    if slc.step is None or slc.step > 0:
        size = slc.stop
    else:
        size = slc.start
    return size


def reverse_slice(sl, size):
    """Reverse a slice.

    Parameters
    ----------
    sl: Slice
        Slice to reverse.
    size: int, optional
        Size of the list to get indices from.
    """
    ind = sl.indices(size)
    shift = [-1, 1][ind[2] < 0]

    start = ind[1] + shift
    stop = ind[0] + shift
    step = -ind[2]

    if stop == -1:
        stop = None

    return slice(start, stop, step)
