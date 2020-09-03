"""Keys for indexing arrays."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import (Any, Iterable, Iterator, List, Optional,
                    Sequence, Union, TYPE_CHECKING)
import logging

import numpy as np

from tomate.custom_types import KeyLike, KeyLikeInt, KeyLikeValue

if TYPE_CHECKING:
    from tomate.coordinates.coord import Coord
    from tomate.coordinates.time import Time
    from tomate.coordinates.coord_str import CoordStr


log = logging.getLogger(__name__)


class Key():
    """Element for indexing an iterable.

    Can be None, int, str, List[int], List[str] or slice.

    See :doc:`../accessor` for more information.

    :param key: Key-like object.
    :attr type: str: {'none', 'int', 'list', 'slice'}
    :attr str: bool: If the key is a string or a list of strings.
    :attr parent_size: int, None: Size of the sequence it would be applied to.
        Useful for reversing keys, or turning slices into lists.
    :attr _size: int, None: Length of what the key would select.
        Is False until size of key is computed.
    """

    INT_TYPES = (int, np.integer)  #: Types that are considered integer.

    def __init__(self, key: KeyLike):
        self.value = None
        self.type = 'none'
        self.str = False

        self._size = False
        self.parent_size = None

        self.set(key)

    @property
    def size(self) -> Optional[int]:
        """Length of what the key would select.

        Integer and None keys have size 0 (they would return a scalar).
        Is None if the size is undecidable (for some slices
        for instance).
        """
        if self._size is False and self.type == 'slice':
            if self.parent_size is not None:
                self._size = len(range(*self.value.indices(self.parent_size)))
            else:
                log.debug("Guessing slice %s size", self.value)
                self._size = guess_slice_size(self.value)
        return self._size

    def set(self, key: KeyLike):
        """Set key value.

        :param TypeError: If key is not valid.
        """
        reject = ''  # Reject message if key is wrong
        s = False    # If key is string
        tp = ''      # Key type

        if isinstance(key, self.INT_TYPES):
            tp = 'int'
            key = int(key)
        elif isinstance(key, str):
            tp = 'int'
            s = True

        elif isinstance(key, (list, tuple, np.ndarray)):
            tp = 'list'
            key = list(key)
            if all(isinstance(z, self.INT_TYPES) for z in key):
                key = [int(z) for z in key]
            elif all(isinstance(z, str) for z in key):
                s = True
            else:
                reject = 'List elements must be all integers or all strings'

        elif isinstance(key, slice):
            tp = 'slice'
            slc = key.start, key.stop, key.step
            if all(isinstance(z, (*self.INT_TYPES, type(None))) for z in slc):
                slc = [int(z) if z is not None else None for z in slc]
            else:
                reject = 'Slice elments must be all None or integers'
            key = slice(*slc)

        elif key is None:
            tp = 'none'

        else:
            reject = ('Invalid type (must be int, str, iterable, or slice),'
                      f' is {type(key)}')

        if reject:
            raise TypeError(f"Key invalid: {reject}")

        self.value = key
        self.type = tp
        self.str = s

        self._size = False
        self._set_size()

    def _set_size(self):
        """Set size if possible.

        Cannot set size from a slice alone, we
        need the length of the iterable it will
        be applied to.
        """
        if self.type == 'int':
            self._size = 0
        elif self.type == 'none':
            self._size = 0
        elif self.type == 'list':
            self._size = len(self.value)

    def __eq__(self, other: 'Key'):
        return self.value == other.value

    def __iter__(self) -> Iterator:
        """Iterate on the key.

        Iterate on list of indices (integers or strings)
        if the key can be converted to one.
        Otherwise iterate on a single slice.
        """
        try:
            val = self.as_list()
        except TypeError:
            val = [self.value]
        return iter(val)

    def copy(self) -> 'Key':
        """Return a copy"""
        if self.type == 'list':
            value = self.value.copy()
        else:
            value = self.value
        key = self.__class__(value)
        key._size = self._size
        key.parent_size = self.parent_size
        return key

    def __repr__(self):
        return '{}: {}'.format(str(self.__class__.__name__), self)

    def __str__(self):
        return str(self.value)

    def set_size_coord(self, coord: Iterable):
        """Set size using a coordinate.

        :param coord: The coordinate that would be used
            (or any iterable of appropriate size).
        :raises IndexError: If slice of size 0.
        """
        self.parent_size = len(coord)
        if self.type == 'slice':
            self._size = len(self.apply(coord))

    def no_int(self) -> KeyLike:
        """Return value but replace int with list."""
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
            if is_none_slice(self.value):
                self.value = slice(None, None, -1)
            else:
                self.set(self.as_list()[::-1])
                self.simplify()

    def simplify(self):
        """Simplify list into a slice if possible.

        Transform a list into a slice if the list is
        a serie of integers of fixed step.
        """
        if self.type == 'list' and not self.str:
            key = list2slice(self.value)
            if isinstance(key, slice):
                self.type = 'slice'
            self.value = key

    def as_list(self) -> Union[List[int], List[str]]:
        """Return list of key.

        :raises TypeError: If is slice and parent size was
            not set, will throw error.
        """
        a = self.value
        if self.type == 'int':
            a = [a]
        elif self.type == 'list':
            a = a.copy()
        elif self.type == 'slice':
            if self.parent_size is None:
                raise TypeError("parent_size must be set to transform"
                                " slice into list")
            a = list(range(*a.indices(self.parent_size)))

        return a

    def apply(self, seq: Sequence,
              int2list: bool = False) -> Union[List[Any], Any]:
        """Apply key to a sequence.

        :param int2list: If True, even if key select single element,
             return list. Default is False.
        :returns: One element or a list of elements from the sequence.
        :raises TypeError: Key type not applicable.
        :raises KeyError: One string key not in sequence.
        """
        if self.str:
            out = []
            for z in self:
                if z not in seq:
                    raise KeyError(f"'{z}' not in sequence")
                out.append(z)
            if self.type == 'int':
                return out[0]
            if self.type == 'list':
                return out

        if self.type == 'list' or (int2list and self.type == 'int'):
            return [seq[z] for z in self]
        if self.type == 'int':
            return seq[self.value]
        if self.type == 'slice':
            return seq[self.value]
        raise TypeError("Key not applicable")

    def __mul__(self, other: 'Key') -> 'Key':
        """Subset key by another.

        If `B = A[self]`
        and `C = B[other]`
        then `C = A[self*other]`
        Operation is not commutative.

        The type of the resulting key is of the strongest
        type of the two keys (int > list > slice).

        :returns: self*other
        :raises TypeError: If other is a string key but not self.
        """
        if self.type == 'slice' and is_none_slice(self.value):
            return other
        if other.type == 'slice' and is_none_slice(other.value):
            return self

        a = self.as_list()
        if other.str and not self.str:
            raise TypeError("Cannot multiply an integer indices key"
                            " by a string indices key")
        out = other.apply(a, int2list=True)

        if self.type == 'int' or other.type == 'int':
            key = self.__class__(out[0])
        elif self.type == 'list' or other.type == 'list':
            key = self.__class__(out)
        else:
            key = self.__class__(list2slice(out))
            key._size = len(out)
            if key._size > 2:
                assert key.type == 'slice', 'slice * slice should be slice'

        key.parent_size = self.parent_size
        return key

    def __add__(self, other: 'Key') -> 'Key':
        """Expand a key by another.

        If `B = A[self]` and `C=A[other]`
        concatenate(B, C) = A[self + other]
        Operation is not commutative (unless followed by a sort).

        The type of the resulting key is a list,
        or a slice if one of the argument is a slice
        and the result can be written as one.

        :returns: self + other
        """
        a = self.as_list()
        b = other.as_list()
        out = a + b

        if self.type == 'slice' or other.type == 'slice':
            out = list2slice(out)

        return self.__class__(out)

    def sort(self):
        """Sort indices in increasing order."""
        if self.type == 'list':
            self.value.sort()
        if self.type == 'slice':
            if self.value.step is not None and self.value.step < 0:
                self.reverse()

    def make_list_int(self):
        """Make list of length one an integer."""
        if self.type == 'list' and self.size == 1:
            self.type = 'int'
            self.value = self.value[0]
            self._size = 0

    def make_int_list(self):
        """Make integer a list of lenght one."""
        if self.type == 'int':
            self.type = 'list'
            self.value = [self.value]
            self._size = 1

    def make_idx_str(self, coord: 'CoordStr'):
        """Transform indices into strings."""
        if not self.str:
            names = coord.get_str_names(self.value)
            self.set(names)
        self.set_size_coord(coord)

    def make_str_idx(self, coord: 'CoordStr'):
        """Transform strings into indices."""
        if self.str:
            idx = coord.get_str_indices(self.value)
            self.set(idx)
        self.set_size_coord(coord)


class KeyValue():
    """KeyLike object storing values.

    Can act like a Key, but missing lot of features
    presently.
    Should not be stored in a keyring.

    A Tuple is considered an 'int'.
    """
    def __init__(self, key: KeyLikeValue):
        self.value = None
        self.type = ''
        self.size = None
        self.set(key)

    def set(self, key: KeyLikeValue):
        """Set value."""
        if isinstance(key, (list, np.ndarray)):
            tp = 'list'
        elif isinstance(key, slice):
            tp = 'slice'
        elif key is None:
            tp = 'none'
        else:
            tp = 'int'

        self.value = key
        self.type = tp
        self._set_size()

    def _set_size(self):
        """Set size."""
        if self.type in ['int', 'none']:
            self.size = 0
        elif self.type == 'list':
            self.size = len(self.value)

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


def is_none_slice(slc) -> bool:
    """Return if slice is equivalent to None slice."""
    is_none = (slc.start in [0, None]
               and slc.stop in [-1, None]
               and slc.step in [1, None])
    return is_none


def list2slice(L: List[int]) -> Union[slice, List[int]]:
    """Transform a list into a slice when possible.

    Step can be any integer.
    Can be descending.
    """
    if len(L) < 2:
        return L

    if np.any(np.sign(L) >= 0) and np.any(np.sign(L) < 0):
        return L

    diff = np.diff(L)

    if len(set(diff)) == 1:
        start = L[0]
        stop = L[-1]
        step = diff[0]

        shift = 1 if step > 0 else -1
        stop += shift
        if ((step > 0 and stop == 0)
                or (step < 0 and stop == -1)):
            stop = None

        return slice(start, stop, step)

    return L


def guess_slice_size(slc: slice) -> Optional[int]:
    """Guess the size of a slice.

    :returns: None if it is not possible to guess.
        (for instance for slice(None, None))
    """
    def get(start, stop, step):
        if abs(step) == 1:
            return abs(stop - start)
        return abs(int(np.ceil((stop - start) / step)))

    start, stop, step = slc.start, slc.stop, slc.step
    if step is None:
        step = 1
    pos = step > 0

    # slice(a, b), a and b of same sign
    if start is not None and stop is not None:
        if start * stop >= 0:
            if (pos and stop == 0) or (not pos and start == 0):
                return 0
            return get(start, stop, step)

    # slice with a None start or stop
    if pos:
        if start is None and stop is not None and stop >= 0:
            return get(0, stop, step)
        if stop is None and start is not None and start < 0:
            return get(start, 0, step)
    else:
        if stop is None and start is not None and start >= 0:
            return get(0, start+1, -step)
        if start is None and stop is not None and stop < 0:
            return get(-1, stop, -step)

    return None


def guess_tolist(slc: slice) -> List[int]:
    """Guess a list of indices without the size.

    NOT MAINTAINED.

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

    raise ValueError(f"Slice ({start}, {stop}, {step}) cannot"
                     " be turned into list by guessing.")


def reverse_slice_order(slc: slice) -> slice:
    """Reverse a slice order.

    NOT MAINTAINED.

    ie the order in which indices are taken.
    The indices themselves do not change.
    We assume the slice is valid (size > 0).
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
