"""Coordinate class.

Routines
--------
select_overlap()
    Find indices too keep a common range across coordinates.

"""

import logging
import bisect

import numpy as np


log = logging.getLogger(__name__)


class Coord():
    """Coordinate object.

    Contains strictly monoteous values.

    Parameters
    ----------
    name: str
        Identification of the coordinate.
    array: Sequence, optional
        Values of the coordinate.
    units: str, optional
        Coordinate units
    name_alt: str or List[str], optional
        Alternative names.
    fullname: str, optional
        Print name.

    Attributes
    ----------
    name: str
        Identification of the coordinate.
    units: str
        Coordinate units.
    name_alt: List[str]
        Alternative names.
    fullname: str
        Print name.
    size: int
        Length of values.
    """

    def __init__(self, name, array=None, units=None, name_alt=None,
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

        if units is None:
            units = ''
        self.units = units

        self._array = None
        self._descending = None
        self._size = 0
        if array is not None:
            self.update_values(array)

    def update_values(self, values):
        """Change values.

        Check if new values are monoteous

        Parameters
        ----------
        array: Sequence
            New values.

        Raises
        ------
        TypeError
            If the data is not 1D.
        ValueError
            If the data is not sorted.
        """
        self._array = np.array(values, dtype=np.float64)
        if len(self._array.shape) > 1:
            raise TypeError("Data not 1D")
        self._size = self._array.size

        diff = np.diff(values)
        if len(diff) > 0:
            desc = np.all(diff < 0)
        else:
            desc = False
        self._descending = desc
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
            Keys asked, passed to a numpy array.

        Returns
        -------
        Numpy array.
        """
        if not self.has_data():
            raise AttributeError("Coordinate '%s' data was not set." % self.name)
        return self._array.__getitem__(y)

    def __str__(self):
        s = []
        s.append(str(type(self)))
        s.append("Name: %s" % self.name)
        s.append("Size: %d" % self.size)
        if self.has_data():
            s.append("Extent: %s" % self.get_extent_str())
            s.append("Descending: %s" % ['no', 'yes'][self.is_descending()])
        if len(self.name_alt) > 0:
            s.append("Alternative names: %s" % ', '.join(self.name_alt))
        if self.units:
            s.append("Units: %s" % self.units)
        return '\n'.join(s)

    def __repr__(self):
        return '\n'.join([super().__repr__(), str(self)])

    def get_extent_str(self) -> str:
        """Return the extent as string."""
        return "%s - %s" % tuple(self.format(v) for v in self.get_extent())

    def copy(self):
        """Return a copy of itself."""
        if self.has_data():
            a = self._array[:]
        else:
            a = None
        return self.__class__(self.name, a, self.units, self.name_alt, self.fullname)

    def slice(self, key):
        """Slice the coordinate."""
        if key is None:
            key = slice(None, None)
        data = self._array[key]
        self.update_values(data)

    def empty(self):
        """Empty values."""
        self._array = None
        self._descending = None
        self._size = 0

    def subset(self, vmin, vmax):
        """Return slice between vmin and vmax (included).

        If descending, the slice is reverted (values are always
        in increasing order).

        Parameters
        ----------
        vmin, vmax: float
            Bounds to select.

        Examples
        --------
        >>> lat = Coord('lat', np.linspace(20, 60, 41))
        ... slice_lat = lat.subset(30, 43)
        ... print(slice_lat)
        slice(10, 24, 1)
        >>> print(lat[slice_lat])
        [30 31 ... 42 43]
        """
        start = self.get_index(vmin, "below")
        stop = self.get_index(vmax, "above")
        if not self.is_descending():
            stop += 1
            step = 1
        else:
            start += 1
            if stop == 0:
                stop = None
            else:
                stop -= 1
            step = -1
        return slice(start, stop, step)

    def is_descending(self) -> bool:
        """Return if coordinate is descending"""
        return self._descending

    def is_regular(self, threshold=1e-5):
        """Return if coordinate values are regularly spaced.

        Float comparison is made to a threshold.
        """
        diff = np.diff(self[:])
        regular = np.all(diff - diff[0] <= threshold)
        return regular

    def has_data(self):
        """If coordinate has data."""
        return self._array is not None

    def get_step(self, threshold=1e-5):
        """Return mean step between values.

        Check if the coordinate is regular up to threshold.
        """
        if not self.is_regular(threshold):
            log.warning("Coordinate '%s' not regular (at precision %s)",
                        self.name, threshold)
        return np.mean(np.diff(self[:]))

    def get_extent(self, slc=None):
        """Return extent.

        ie first and last values

        Parameters
        ----------
        slc: slice
            Constrain extent to a slice.

        Returns
        -------
        List[float]
            First and last values.
        """
        if slc is None:
            slc = slice(None, None)
        values = self._array[slc]
        return list(values[[0, -1]])

    def get_limits(self, slc=None):
        """Return min/max

        Returns
        -------
        List[float]
            Min and max
        """
        lim = self.get_extent(slc)
        if self._descending:
            lim = lim[::-1]
        return lim

    def get_index(self, value, loc='closest'):
        # REVIEW
        """Return index of the element closest to `value`.

        Can return the index of the closest element above, below
        or from both sides to the specified value.

        Parameters
        ----------
        value: float
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

    @staticmethod
    def format(value, fmt='{:.2f}'):
        """Format a scalar value."""
        return fmt.format(value)

    def get_collocated(self, other):
        """Return indices of identical values.

        Parameters
        ----------
        other: Coord
            Other coordinate.

        Returns
        -------
        idx_self, idx_other: List[int]
            List of indices for both coordinates, where
            their values are identical.
        """
        values = {v for v in self[:] if v in other[:]}

        idx_self = [self.get_index(v) for v in values]
        idx_other = [other.get_index(v) for v in values]

        return idx_self, idx_other

    def get_collocated_float(self, other, threshold=1e-5):
        """Return indices of values closer than a threshold.

        Parameters
        ----------
        other: Coord
            Other coordinate.

        Returns
        -------
        idx_self, idx_other: List[int]
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


def select_overlap(*coords):
    # REVIEW
    """Return list of slices overlapping.

    Parameters
    ----------
    coords: List[Coord]

    Returns
    -------
    slices: List[Slice]
        Slice for each coordinate so that the selected
        values have the same extent.
    """

    limits = [c.get_limits() for c in coords]
    mins = [z[0] for z in limits]
    maxs = [z[1] for z in limits]

    mn = max(mins)
    mx = min(maxs)

    slices = [c.subset(mn, mx) for c in coords]

    return slices
