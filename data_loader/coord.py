"""Coordinate class.

Contains strictly monoteous values.
Stores name of the coordinate, its fullname,
and the alternative name it could be found under in files.
Also stores its unit.


Contains
--------

Coord:
    Coordinate object


Routines
--------

select_overlap()
    Find indices too keep a common range across coordinates.

"""

from typing import List
import bisect

import numpy as np


class Coord():
    """Coordinate object.

    Contains strictly monoteous values.

    Parameters
    ----------
    name: str
        Identification of the coordinate
    array: Sequence, optional
        Values of the coordinate
    unit: str, optional
        Coordinate unit
    name_alt: str or List of str, optional
        Alternative names
    fullname: str, optional
        Print name

    Attributes
    ----------
    name: str
        Identification of the coordinate
    unit: str
        Coordinate unit
    name_alt: List of str
        Alternative names
    fullname: str
        Print name
    size: int
        Length of values
    """
    def __init__(self, name, array=None, unit=None, name_alt=None,
                 fullname=None):
        self.name = name
        if name_alt is None:
            name_alt = []
        if isinstance(name_alt, str):
            name_alt = [name_alt]
        self.name_alt = name_alt

        if fullname is None:
            fullname = ""
        self.fullname = fullname

        if unit is None:
            unit = ''
        self.unit = unit

        self._array = None
        self._descending = None
        self._size = None
        if array is not None:
            self.update_values(array)

    def update_values(self, values):
        """Change values.

        Check if monoteous

        Parameters
        ----------
        array: Sequence
            New values

        Raises
        ------
        TypeError
            If the data is not 1D.
        ValueError
            If the data is not sorted.
        """
        self._array = np.array(values)
        if len(self._array.shape) > 1:
            raise TypeError("Data not 1D")
        self._size = self._array.size

        self._descending = np.all(np.diff(values) < 0)
        if not np.all(np.diff(values) > 0) and not self._descending:
            raise ValueError("Data not sorted")

    @property
    def size(self):
        """Length of coordinate."""
        return self._size

    def __getitem__(self, y):
        """Use numpy getitem for the array.

        Parameters
        ----------
        y: Numpy access
            Keys asked, passed to a numpy array

        Returns
        -------
        Numpy array
        """
        return self._array.__getitem__(y)

    def __str__(self):
        s = []
        s.append(str(type(self)))
        s.append('name: ' + self.name)
        s.append('extent: ' + self.get_extent_str())
        s.append('size: ' + str(self.size))
        return '\n'.join(s)

    def get_extent_str(self) -> str:
        """Return the extent as str."""
        return "{0} - {1}".format(*self.get_extent())

    def copy(self):
        """Return a copy of itself"""
        if self._array is not None:
            a = self._array[:]
        else:
            a = None
        return self.__class__(self.name, a, self.unit, self.name_alt)

    def slice(self, key):
        """Slice the coordinate."""
        data = self._array[key]
        self.update_values(data)

    def subset(self, vmin: float, vmax: float) -> [int, int]:
        # REVIEW
        """Return index for slicing between vmin and vmax.

        vmin and vmax are included
        """
        i1 = self.get_index(vmin, "below")
        i2 = self.get_index(vmax, "above") + 1
        return i1, i2

    def is_descending(self) -> bool:
        """Return if coordinate is descending"""
        return self._descending

    def get_extent(self) -> [float, float]:
        """Return extent.

        ie first and last values
        """
        return list(self._array[[0, -1]])

    def get_limits(self) -> [float, float]:
        """Return min/max"""
        lim = self.get_extent()
        if self._descending:
            lim = lim[::-1]
        return lim

    def get_index(self, value: float, loc: str = 'closest') -> int:
        # REVIEW
        """Return index closest to value

        loc: specifies what index to choose
             {closest | below | above}
        """
        loc_ = {'below': ['left', 'right'][self._descending],
                'above': ['right', 'left'][self._descending],
                'closest': 'closest'}[loc]

        C = self._array[::[1, -1][self._descending]]

        idx = get_closest(C, value, loc_)

        if self._descending:
            idx = self.size-idx - 1

        return idx


def get_closest(L, elt, loc='closest'):
    """Return index closest to elt in L.

    L is a ascending sorted list
    loc: 'closest' -> take closest elt
          'left' -> take closest to the left
          'right' -> take closest to the right
    If two numbers are equally close, return the smallest number.
    """

    loc_opt = ['left', 'right', 'closest']
    if loc not in loc_opt:
        raise ValueError(
            "Invalid loc type. Expected one of: %s" % loc_opt)

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
            out = pos-1

    elif loc == 'right':
        out = pos

    return out


def select_overlap(*coords: List[Coord]) -> List[List[int]]:
    # REVIEW
    """Return list of slices overlapping.

    coords: list of Coord
    """

    limits = [c.get_limits() for c in coords]
    mins = [z[0] for z in limits]
    maxs = [z[1] for z in limits]

    mn = max(mins)
    mx = min(maxs)

    idx = [c.subset(mn, mx) for c in coords]

    return idx
