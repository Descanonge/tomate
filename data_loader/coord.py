"""Coordinate class.

Contains strictly monoteous values.
Stores name of the coordinate, its fullname,
and the alternative name it could be found under.
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

import numpy as np

import mypack.analysis as mpa

from data_loader.stubs import NpIdx


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
    name_alt: List[str], optional
        Alternative names
    fullname: str, optional
        Print name

    Attributes
    ----------
    name: str
        Identification of the coordinate
    unit: str
        Coordinate unit
    name_alt: List[str]
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

    def __getitem__(self, y: NpIdx):
        """Use numpy getitem for the array."""
        return self._array.__getitem__(y)

    def __str__(self):
        s = str(type(self)) + '\n'
        s += 'name: ' + self.name + '\n'
        s += 'extent: ' + str(self.get_extent()) + '\n'
        s += 'size: ' + str(self.size) + '\n'
        return s

    def copy(self):
        """Return a copy of itself"""
        if self._array is not None:
            a = self._array[:]
        else:
            a = None
        return Coord(self.name, a, self.unit, self.name_alt)

    def slice(self, key: NpIdx):
        """Subset the coordinate."""
        self._array = self._array[key]
        self._descending = np.all(np.diff(self._array) < 0)
        self._size = self._array.size

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

        idx = mpa.get_closest(C, value, loc_)

        if self._descending:
            idx = self.size-idx - 1

        return idx


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
