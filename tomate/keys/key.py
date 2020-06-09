"""Keys for indexing arrays."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import Iterator, List, Optional, Sequence, Union, TYPE_CHECKING

import numpy as np

from tomate.custom_types import KeyLikeInt, KeyLikeVar, KeyLikeValue

if TYPE_CHECKING:
    from tomate.coordinates.coord import Coord
    from tomate.coordinates.time import Time
    from tomate.coordinates.variables import Variables


class Key():
    """Element for indexing a dimension of an array.

    Can be None, int, List[int] or slice.

    See :doc:`../accessor` for more information.

    :param key: Key-like object.

    INT_TYPES: List[Type]

    :attr type: str: {'none', 'int', 'list', 'slice'}
    :attr parent_size: int, None: Size of the sequence it would be applied to.
        Useful for reversing keys, or turning slices into lists.
    :attr shape: int, None: Length of what the key would select.
        Integer and None keys have shape 0 (they would get
        a scalar).
        Is None if the shape is undecidable (for some slices
        for instance).
    """

    INT_TYPES = (int, np.integer)  #: Types that are considered integer.

    def __init__(self, key: KeyLikeInt):
        self.value = None
        self.type = ''
        self.shape = None
        self.parent_size = None
        self.set(key)

    def set(self, key: KeyLikeInt):
        """Set key value.

        :param key: Key-like:
        :param TypeError: If key is not a valid type.
        """
        reject = False
        if isinstance(key, (list, tuple, np.ndarray)):
            reject = any(not isinstance(z, self.INT_TYPES) for z in key)
            tp = 'list'
            key = [int(k) for k in key]
            if len(key) == 0:
                raise IndexError("Key cannot be an empty list.")
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
            raise TypeError(f"Key is not int, List[int], or slice (is {type(key)})")
        self.value = key
        self.type = tp
        self.set_shape()

    def __eq__(self, other: 'Key') -> bool:
        return self.value == other.value

    def __repr__(self):
        return str(self.value)

    def __iter__(self) -> Iterator[KeyLikeInt]:
        """Iter through values."""
        try:
            val = self.tolist()
        except TypeError:
            val = [self.value]
        return iter(val)

    def copy(self) -> 'Key':
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

        :raises IndexError: If slice of shape 0.
        """
        if self.type == 'int':
            self.shape = 0
        elif self.type == 'list':
            self.shape = len(self.value)
        elif self.type == 'none':
            self.shape = 0
        elif self.type == 'slice':
            self.shape = guess_slice_shape(self.value)
            if self.shape == 0:
                raise IndexError(f"Invalid slice ({self.value}) of shape 0.")

    def set_shape_coord(self, coord: 'Coord'):
        """Set shape using a coordinate.

        :param coord: The coordinate that would be used.
        :raises IndexError: If slice of shape 0.
        """
        self.parent_size = coord.size
        if self.type == 'slice':
            self.shape = len(coord[self.value])
            if self.shape == 0:
                raise IndexError(f"Invalid slice ({self.value}) of shape 0.")

    def no_int(self) -> Union[List[int], slice, None]:
        """Return value, replaces int with list."""
        if self.type == 'int':
            return [self.value]
        return self.value

    def reverse(self):
        """Reverse key.

        Equivalent to a [::-1].
        """
        if self.type == 'list':
            self.value = self.value[::-1]
        elif self.type == 'slice':
            self.value = reverse_slice_order(self.value)

    def simplify(self):
        """Simplify list into a slice.

        Transform a list into a slice if the list is
        a serie of integers of fixed step.
        """
        if self.type == 'list':
            key = list2slice_simple(self.value)
            if isinstance(key, slice):
                self.type = 'slice'
            self.value = key

    def tolist(self) -> List[int]:
        """Return list of key."""
        a = self.value
        if self.type == 'int':
            a = [a]
        elif self.type == 'list':
            a = a.copy()
        elif self.type == 'slice':
            if self.parent_size is not None:
                a = list(range(*self.value.indices(self.parent_size)))
            else:
                a = guess_tolist(self.value)

        elif self.type == 'none':
            a = []
        return a

    def apply(self, seq: Sequence) -> Sequence:
        """Apply key to a sequence.

        :raises TypeError: Key type not applicable.
        """
        if self.type == 'int':
            return seq[self.value]
        if self.type == 'list':
            return [seq[i] for i in self.value]
        if self.type == 'slice':
            return seq[self.value]
        raise TypeError(f"Not applicable (key type '{self.type}').")

    def __mul__(self, other: 'Key') -> 'Key':
        """Subset key by another.

        If `B = A[self]`
        and `C = B[other]`
        then `C = A[self*other]`

        The type of the resulting key is of the strongest
        type of the two keys (int > list > slice).

        :returns: self*other
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

    def __add__(self, other: 'Key') -> 'Key':
        """Expand a key by another.

        If `B = A[self]` and `C=A[other]`
        concatenate(B, C) = A[self + other]

        The type of the resulting key is a list,
        or a slice if one of the argument is a slice
        and the result can be written as one.

        :returns: self + other
        """
        a = self.tolist()
        b = other.tolist()
        key = a + b

        if self.type == 'slice' or other.type == 'slice':
            key = list2slice_simple(key)

        return self.__class__(key)

    def sort(self):
        """Sort indices."""
        if self.type == 'list':
            self.value = list(set(self.value))
            self.value.sort()
        if self.type == 'slice':
            if self.value.step is not None and self.value.step < 0:
                self.reverse()

    def make_list_int(self):
        """Make list of length one an integer."""
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

    :param key: Key-like object.
        Can also be variable name, list of variables names, or
        a slice made from strings.

    :attr var: bool: If the key-value can be used only for variables
        (*ie* it is or contains a string). In which case
        one can use `make_var_idx`.

    Examples
    --------
    Examples of values:
    >>> 0, [0, 1], 'sst', ['sst'], slice('sst', 'chl', 1)
    """

    def __init__(self, key: KeyLikeVar):
        self.var = False
        super().__init__(key)

    def set(self, key: KeyLikeVar):
        """Set value.

        :param key: Can be integer or string.
            Can be list of integers or strings (not a mix of both).
            Can be a slice. Step must be None or integer. Start and
            Stop can be integers or strings (not a mix of both).

        :raises TypeError: Key is not of valid type.
        :raises ValueError: Slice is not valid (step is not integer,
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
            if len(key) == 0:
                raise IndexError("Key cannot be an empty list.")
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
                            f" (is {type(key)})")
        self.value = key
        self.type = tp
        self.var = var
        self.set_shape()

    def set_shape(self):
        if self.type == 'slice' and self.var:
            self.shape = None
        else:
            super().set_shape()

    def reverse(self):
        if not (self.var and self.type == 'slice'):
            super().reverse()

    def simplify(self):
        if not self.var:
            super().simplify()

    def tolist(self) -> List[int]:
        """Return list of key.

        :raises TypeError: If string slice cannot be transformed into list.
        """
        if self.type == 'slice' and self.var:
            raise TypeError("Variable slice cannot be transformed into list.")
        return super().tolist()

    def __mul__(self, other: 'KeyVar') -> 'KeyVar':
        """Subset key bd another.

        See Key.__mul__ for details.

        :raises TypeError: If `other` value is a KeyLikeStr, then
            `self` must be too.
        """
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

    def make_idx_var(self, variables: 'Variables'):
        """Transform indices into variables names."""
        if not self.var:
            names = variables.get_var_names(self.value)
            self.set(names)
        self.set_shape_coord(variables)

    def make_var_idx(self, variables: 'Variables'):
        """Transform variables names into indices."""
        if self.var:
            idx = variables.get_var_indices(self.value)
            self.set(idx)
        self.set_shape_coord(variables)


class KeyValue():
    """KeyLike object storing values.

    Can act like a Key, but missing lot of features
    presently.
    Should not be stored in a keyring.
    """
    def __init__(self, key: KeyLikeValue):
        self.value = None
        self.type = ''
        self.shape = None
        self.set(key)

    def set(self, key: KeyLikeValue):
        """Set value."""
        if isinstance(key, (list, tuple, np.ndarray)):
            tp = 'list'
        elif isinstance(key, slice):
            tp = 'slice'
        elif key is None:
            tp = 'none'
        else:
            tp = 'int'

        self.value = key
        self.type = tp
        self.set_shape()

    def set_shape(self):
        """Set shape."""
        if self.type in ['int', 'none']:
            self.shape = 0
        elif self.type == 'list':
            self.shape = len(self.value)

    def apply(self, coord: 'Coord') -> KeyLikeInt:
        """Find corresponding index."""
        if self.type == 'int':
            return coord.get_index(self.value)
        if self.type == 'list':
            return coord.get_indices(self.value)
        if self.type == 'slice':
            return coord.subset(self.value.start, self.value.stop)
        raise TypeError(f"Not applicable (key type '{self.type}').")

    def apply_by_day(self, coord: 'Time') -> KeyLikeInt:
        """Find corresponding index on same day."""
        if self.type == 'int':
            return coord.get_index_by_day(self.value)
        if self.type == 'list':
            return coord.get_indices_by_day(self.value)
        if self.type == 'slice':
            return coord.subset_by_day(self.value.start, self.value.stop)
        raise TypeError(f"Not applicable (key type '{self.type}')")


def simplify_key(key: KeyLikeInt) -> KeyLikeInt:
    """Simplify a key.

    Transform a list into a slice if the list is
    a serie of integers of fixed step.
    """
    if isinstance(key, (list, tuple, np.ndarray)):
        key = list2slice_simple(list(key))
    return key


def list2slice_simple(L: List[int]) -> Union[slice, List[int]]:
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


def list2slice_complex(L: List[int]) -> Union[slice, List[int]]:
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


def guess_slice_shape(slc: slice) -> Optional[int]:
    """Guess the shape of a slice.

    :returns: None if it is not possible to guess.
        (for instance for slice(None, None))
    """

    start, stop, step = slc.start, slc.stop, slc.step
    pos = step is None or step > 0
    if start is not None and stop is not None:
        if start * stop >= 0:
            if start > stop if pos else start < stop:
                return 0
            return abs(stop - start)

    if pos:
        if start is None and stop is not None and stop >= 0:
            return stop
        if stop is None and start is not None and start < 0:
            return -start
    else:
        if stop is None and start is not None and start >= 0:
            return start
        if start is None and stop is not None and stop < 0:
            return -stop - 1

    return None


def guess_tolist(slc: slice) -> List[int]:
    """Guess a list of indices without the size.

    Transforming a slice into a list of indices requires
    the size of the sequence the slice is destined for.
    >>> indices = slice(0, 5).indices(size)

    In some cases, it is possible to make a guess:
    slice(a, b); a and b of same sign
    slice(None, a, s>0); a > 0
    slice(a, None, s>0); a < 0
    slice(None, a, s<0); a < 0
    slice(a, None, s<0); a > 0

    :raises ValueError: If cannot guess.
    """
    start, stop, step = slc.start, slc.stop, slc.step
    if step is None:
        step = 1

    if start is not None and stop is not None:
        if start * stop >= 0:
            return list(range(start, stop, step))

    if step > 0:
        if start is None and stop is not None and stop >= 0:
            return list(range(0, stop, step))
        if stop is None and start is not None and start < 0:
            return list(range(start, 0, step))
    else:
        if stop is None and start is not None and start >= 0:
            return list(range(start, 0, step))
        if start is None and stop is not None and stop < 0:
            return list(range(-1, stop, step))

    raise ValueError(f"Slice ({slc}) cannot be turned into list by guessing.")


def reverse_slice_order(slc: slice) -> slice:
    """Reverse a slice order.

    ie the order in which indices are taken.
    The indices themselves do not change.
    We assume the slice is valid (shape > 0).
   """
    start, stop, step = slc.start, slc.stop, slc.step
    if step is None:
        step = 1

    shift = [1, -1][step > 0]
    over = [-1, 0][step > 0]
    if start is not None:
        if start == over:
            start = None
        else:
            start += shift
    if stop is not None:
        if stop == over:
            stop = None
        else:
            stop += shift

    step *= -1
    start, stop = stop, start
    return slice(start, stop, step)
