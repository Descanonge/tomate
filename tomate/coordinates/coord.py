"""Coordinates."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import logging
import bisect
from typing import Any, List, Optional, Sequence, Tuple, Union

import numpy as np

from tomate.keys.key import reverse_slice_order
from tomate.custom_types import KeyLike


log = logging.getLogger(__name__)


class Coord():
    """Coordinate object.

    Contains strictly monoteous values.

    :param name: str: Identification of the coordinate.
    :param array: [opt] Values of the coordinate.
    :param units: [opt] Coordinate units
    :param fullname: [opt] Print name.

    :attr name: str: Name of coordinate.
    :attr units: str: Coordinate units.
    :attr fullname: str: Print name.
    :attr float_comparison: float: Threshold for float comparison.
    """

    def __init__(self, name: str,
                 array: Sequence = None,
                 units: str = None, fullname: str = None):
        self.name = name

        if fullname is None:
            fullname = ""
        self.fullname = fullname

        if units is None:
            units = ''
        self.units = units

        self.float_comparison = 1e-9

        self._array = None
        self._descending = None
        self._size = None
        if array is not None:
            self.update_values(array)

    def update_values(self, values: Sequence, dtype=None):
        """Change values.

        Check if new values are monoteous

        :param values: New values.
        :param dtype: [opt] Dtype of the array.
            Default to np.float64
        :type dtype: data-type

        :raises TypeError: If the data is not 1D.
        :raises ValueError: If the data is not sorted.
        """
        if dtype is None:
            dtype = np.float64
        self._array = np.array(values, dtype=dtype)
        if len(self._array.shape) == 0:
            self._array = self._array.reshape(1)
        elif len(self._array.shape) > 1:
            raise TypeError("Data not 1D")
        self._size = self._array.size

        diff = np.diff(self._array)
        if len(diff) > 0:
            desc = np.all(diff < 0)
        else:
            desc = False
        self._descending = desc
        if not np.all(diff > 0) and not self._descending:
            raise ValueError("Data not sorted")

    def __len__(self) -> int:
        return self.size

    @property
    def size(self) -> int:
        """Length of coordinate."""
        return self._size

    def __getitem__(self, y: KeyLike) -> np.ndarray:
        """Use numpy getitem for the array."""
        if not self.has_data():
            raise AttributeError(f"Coordinate '{self.name}' data was not set.")
        return self._array.__getitem__(y)

    def __repr__(self):
        s = []
        s.append(str(type(self)))
        s.append(f"Name: {self.name}")
        if self.fullname:
            s.append(f"Fullname: {self.fullname}")
        if self.has_data():
            s.append(f"Size: {self.size}")
            s.append(f"Extent: {self.get_extent_str()}")
            s.append(f"Descending: {'yes' if self.is_descending() else 'no'}")
        if self.units:
            s.append(f"Units: {self.units}")
        return '\n'.join(s)

    def set_attr(self, name: str, attr: Any):
        """Set attribute.

        :param name: Name of the attribute.
            Only 'units' and 'fullname' supported.
        :param attr: Value of the attribute.
        """
        if name not in ('units', 'fullname'):
            raise AttributeError(f"'{name}' attribute cannot be set")
        if name == 'units':
            self.units = attr
        elif name == 'fullname':
            self.fullname = attr

    def get_extent_str(self, slc: KeyLike = None) -> str:
        """Return the extent as string.

        :param slc: [opt]
        """
        if self.size == 1:
            return self.format(self._array[0])
        s = "{} - {}".format(*[self.format(v)
                               for v in self.get_extent(slc)])
        return s

    def copy(self) -> "Coord":
        """Return a copy of itself."""
        return self.__class__(self.name, self._array, self.units, self.fullname)

    def slice(self, key: KeyLike):
        """Slice the coordinate.

        :raises IndexError: If there is no data.
        """
        if not self.has_data():
            raise IndexError("Coordinate has no values to slice.")
        if key is None:
            key = slice(None, None)
        data = self._array[key]
        self.update_values(data)

    def empty(self):
        """Empty values."""
        self._array = None
        self._descending = None
        self._size = None

    def subset(self, vmin: float = None, vmax: float = None,
               exclude: bool = False) -> slice:
        """Return slice between vmin and vmax.

        If descending, the slice is reverted (values are always
        in increasing order).

        :param vmin, vmax: [opt] Bounds to select.
            If None, min and max of coordinate are taken.
        :param exclude: [opt] If True, exclude vmin and vmax from selection.
            Default is False.

        Examples
        --------
        >>> lat = Coord('lat', np.linspace(20, 60, 41))
        ... slice_lat = lat.subset(30, 43)
        ... print(slice_lat)
        slice(10, 24, 1)
        >>> print(lat[slice_lat])
        [30 31 ... 42 43]
        """
        if vmin is None:
            start = 0
        else:
            start = self.get_index(vmin, ["below", "above"][exclude])
        if vmax is None:
            stop = self.size
        else:
            stop = self.get_index(vmax, ["above", "below"][exclude])

        step = [1, -1][self.is_descending()]
        stop += step
        if stop < 0:
            stop = None
        slc = slice(start, stop, step)

        # Untested
        if self.is_descending():
            slc = reverse_slice_order(slc)

        return slc

    def select(self, vmin: float = None, vmax: float = None,
               exclude: bool = False) -> np.ndarray:
        """Select values slice.

        :param vmin: [opt]
        :param vmax: [opt]
        :param exclude: [opt]
        """
        return self._array[self.subset(vmin, vmax, exclude)]

    def is_descending(self) -> bool:
        """Return if coordinate is descending"""
        return self._descending

    def is_regular(self, threshold: float = 1e-5) -> bool:
        """Return if coordinate values are regularly spaced.

        Float comparison is made to a threshold.
        """
        diff = np.diff(self[:])
        regular = np.all(diff - diff[0] <= threshold)
        return regular

    def has_data(self) -> bool:
        """If coordinate has data."""
        return self._array is not None

    def change_units(self, new: str):
        """Change units.

        :param new: New units.
        """
        self.update_values(self.change_units_other(self._array, self.units, new))
        self.units = new

    @staticmethod
    def change_units_other(values: Sequence, old: str, new: str):
        """Change units of a sequence of values."""
        raise NotImplementedError("change_units_other not implemented.")

    def get_step(self, threshold: float = 1e-5) -> float:
        """Return mean step between values.

        Check if the coordinate is regular up to threshold.
        """
        if not self.is_regular(threshold):
            log.warning("Coordinate '{}' not regular (at precision %s)",
                        self.name, threshold)
        return np.mean(np.diff(self[:]))

    def get_extent(self, slc: Union[List[int], slice] = None) -> List[float]:
        """Return extent.

        ie first and last values

        :param slc: [opt] Constrain extent to a slice.
        :returns: First and last values.
        """
        if slc is None:
            slc = slice(None, None)
        values = self._array[slc]
        return list(values[[0, -1]])

    def get_limits(self, slc: Union[List[int], slice] = None) -> List[float]:
        """Return min/max

        :param slc: [opt] Constrain extent with a slice.
        :returns: Min and max
        """
        lim = self.get_extent(slc)
        if self._descending:
            lim = lim[::-1]
        return lim

    def get_index(self, value: float, loc: str = 'closest') -> int:
        """Return index of the element closest to `value`.

        Can return the index of the closest element above, below
        or from both sides to the specified value.

        loc: {'closest', 'below', 'above'}
            What index to choose.
        """
        loc_ = {'below': 'left',
                'above': 'right',
                'closest': 'closest'}[loc]

        C = self._array[::[1, -1][self._descending]]

        idx = get_closest(C, value, loc_)

        if self._descending:
            idx = self.size-idx - 1

        return idx

    def get_indices(self, values: Sequence[float], loc: str = 'closest') -> List[int]:
        """Return indices of the elements closest to values.

        loc: {'closest', 'below', 'above'}
        """
        indices = [self.get_index(v, loc) for v in values]
        return indices

    def get_index_exact(self, value: float) -> Optional[int]:
        """Return index of value if present.

        None if value is not present.
        """
        idx = np.where(np.abs(self._array - value) < self.float_comparison)[0]
        if len(idx) == 0:
            return None
        return idx[0]

    @staticmethod
    def format(value: float, fmt: str = '{:.2f}') -> str:
        """Format a scalar value."""
        return fmt.format(value)

    def get_collocated(self, other: "Coord") -> Tuple[List[int], List[int]]:
        """Return indices of identical values.

        :param other: Other coordinate.

        :returns: idx_self, idx_other:
            List of indices for both coordinates, where
            their values are identical.
        """
        values = {v for v in self[:] if v in other[:]}

        idx_self = [self.get_index(v) for v in values]
        idx_other = [other.get_index(v) for v in values]

        return idx_self, idx_other

    def get_collocated_float(self, other: "Coord",
                             threshold: float = 1e-5) -> Tuple[List[int], List[int]]:
        """Return indices of values closer than a threshold.

        :param other: Other coordinate.

        :returns: idx_self, idx_other:
            List of indices for both coordinates, where
            their values less than `threshold` apart.
        """
        idx_self = []
        idx_other = []
        for i, v in enumerate(self[:]):
            i_other = other.get_index(v, loc='closest')
            v_other = other[i_other]
            if abs(v - v_other) < threshold:
                idx_self.append(i)
                idx_other.append(i_other)

        return idx_self, idx_other


def get_closest(L: List[float], elt: float, loc: str = 'closest') -> int:
    """Return index closest to elt in L.

    If two numbers are equally close, return the smallest number.

    :param L: Ascending sorted list
    :param loc:
        'closest' -> take closest elt,
        'left' -> take closest to the left,
        'right' -> take closest to the right,

    :raises TypeError: If loc is invalid.
    """

    loc_opt = ['left', 'right', 'closest']
    if loc not in loc_opt:
        raise TypeError("Invalid loc type."
                        " Expected one of: 'left', 'right', 'closest'")

    pos = bisect.bisect_left(L, elt)
    if pos == 0:
        out = pos
    elif pos == len(L):
        out = len(L)-1

    elif loc == 'closest':
        if elt - L[pos-1] <= L[pos] - elt:
            out = pos-1
        else:
            out = pos

    elif loc == 'left':
        if elt == L[pos]:
            out = pos
        else:
            pos = out-1

    elif loc == 'right':
        out = pos

    return out
