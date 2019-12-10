"""Coordinate scanning.

Handles scanning of the filenames, and of the
coordinate values inside files.

Contains
--------

Matcher:
    Keep info on a matcher in the pre-regex

CoordScan:
    Abstract class dynamically derived from a subclass of Coord
    Each object is parented to a Coord so that
    once scanned, the values can be transferred.

CoordScanShared:
    The dimension / coordinate is shared accross multiple files.

CoordScanIn:
    The values are fully contained in the file
"""

from types import MethodType
from typing import List

import numpy as np

from data_loader.coord import Coord


class Matcher():
    """Object associated with a matcher in the pre-regex.

    Holds (temporarily) the match for the current file.

    Parameters
    ----------
    pregex: str
        Matcher pre-regex
    idx: int
        Index in the full pre-regex

    Attributes
    ----------
    coord: str
        Coordinate name
    idx: int
        Matcher index in the full pre-regex
    elt: str
        Coordinate element
    dummy: bool
        If the matcher is a dummy, not containing any
        information, or redondant information.
    ELT_RGX: Dict
        Regex str for each type of element
    """

    ELT_RGX = {"idx": r"\d*",
               "Y": r"\d\d\d\d",
               "yy": r"\d\d",
               "M": r"[a-zA-Z]*",
               "mm": r"\d?\d",
               "dd": r"\d?\d",
               "doy": r"\d?\d?\d",
               "text": r"[a-zA-Z]*",
               "char": r"\S*"}

    def __init__(self, m, idx):
        coord = m.group(1)
        elt = m.group(2)
        custom = m.group('cus')
        rgx = m.group(4)[:-1]
        dummy = m.group(5)

        if elt == '':
            elt = 'idx'

        self.coord = coord
        self.elt = elt
        self.idx = idx
        self.dummy = dummy is not None

        if custom is not None:
            self.rgx = rgx
        else:
            self.rgx = self.ELT_RGX[elt]


class CoordScan(Coord):
    # TODO: keep overlap in memory to load the slice in file.
    """Abstract Coord used for scanning of one variable.

    Parameters
    ----------
    filegroup: Filegroup
        Corresponding filegroup
    coord: Coord
        Parent coordinate
    shared: bool
        If the coordinate is shared accross files.

    Attributes
    ----------
    coord: Coord
        parent coordinate object
    shared: str
        If the coordinate is shared accross files
    values: List[float]
        Temporary list of values found for this coordinate
    in_idx: List[int]
        List of the index for each value inside the files
    scan: set
        What part of the file is to be scanned
        { in | filename | manual } or a combination of the three
    """

    def __init__(self, filegroup, coord: Coord, shared: bool):
        self.filegroup = filegroup
        self.coord = coord

        self.shared = shared
        self.scan = set()

        self.values = []
        self.in_idx = []

        self._idx_descending = False

        super().__init__(coord.name, coord._array, coord.unit, coord.name_alt)

    def is_idx_descending(self):
        """Is idx descending."""
        return self._idx_descending

    def set_values(self, values: List):
        """Set values."""
        self.values = values

    def assign_values(self):
        """Update parent coord with found values."""
        self.coord.update_values(self._array)

    def sort_values(self):
        """Sort by values."""
        self.values = np.array(self.values)
        self.in_idx = np.array(self.in_idx)

        order = np.argsort(self.values)
        self.values = self.values[order]
        self.in_idx = self.in_idx[order]

        if self.in_idx.dtype.kind in 'iuf':
            self._idx_descending = np.all(np.diff(self.in_idx) < 0)

        return order

    def set_idx_descending(self):
        """Set coordinate as descending."""
        self._idx_descending = True

    def reverse_key(self, key):
        """Reverse asked key."""
        if isinstance(key, list):
            key = [self.coord.size - z for z in key]
        elif isinstance(key, slice):
            key = reverse_slice(key, self.coord.size)

        return key

    def get_in_idx(self, key):
        """Get the in file indices.

        Give the index inside the file corresponding to the
        asked values.
        If all the index are contiguous, return a slice

        Parameters
        ----------
        key: Slice or List[int]

        Returns
        -------
        key_data: List[int] or Slice
        """
        if self.size is None:
            key_data = key
            if self.is_idx_descending():
                key_data = self.reverse_key(key)
        else:
            key_data = self.in_idx[key]

        if isinstance(key_data, (list, np.ndarray)):
            diff = np.diff(key_data)
            if np.all(diff == 1):
                start = key_data[0]
                stop = key_data[-1] + 1
                step = 1
            elif np.all(diff == -1):
                start = key_data[0]
                stop = key_data[-1]
                step = -1
                if stop == 0:
                    stop = None
                else:
                    stop -= 1

            key_data = slice(start, stop, step)

        return key_data

    def scan_filename(self, m): # pylint: disable=method-hidden
        """Scan filename to find values.

        Parameters
        ----------
        m: re.match
            match of the filename against the regex

        Returns
        -------
        values: List[float]
            Values found

        Raises
        ------
        NotImplementedError
            If scan_filename was not set.
        """
        raise NotImplementedError("scan_filename was not set for (%s)" % self.name)

    def scan_in_file(self, filename, values): # pylint: disable=method-hidden
        """Scan inside file.

        Scan file to find values and in file indices.

        Parameters
        ----------
        filename: str
            fFilename
        values: List[float]
            Values found previously in filename

        Returns
        -------
        values: List[float]
            Values found in file
        in_idx: List[int]
            Indices of values in file

        Raises
        ------
        NotImplementedError
            If scan_in_file was not set.
        """
        raise NotImplementedError("scan_in_file was not set for (%s)" % self.name)

    def set_scan_filename_func(self, func):
        """Set function for scanning values.

        Parameters
        ----------
        func: Callable[[CoordScan, re.match], values: List[float]]
            Function that recover values from filename
        """
        self.scan.add("filename")
        self.scan_filename = MethodType(func, self)

    def set_scan_in_file_func(self, func):
        """Set function for scanning values in file.

        Parameters
        ----------
        func: Callable[[CoordScan, filename: str, values: List[float]],
                       values: List[float], in_idx: List[int]]
        """
        self.scan.add("in")
        self.scan_in_file = MethodType(func, self)

    def set_scan_manual(self, values, in_idx):
        """Set values manually."""
        self.scan = set(['manual'])
        self.set_values(values)
        self.in_idx = in_idx

    def scan_file_values(self, filename):
        """Find values for a file.

        Parameters
        ----------
        filename: str
            Filename

        Returns
        -------
        Number of values found

        Raises
        ------
        IndexError
            If not as many values as in file indices were found
        """
        values = None
        in_idx = None
        if 'filename' in self.scan:
            values = self.scan_filename() # pylint: disable=not-callable
        if 'in' in self.scan:
            values, in_idx = self.scan_in_file(filename, values) # pylint: disable=not-callable

        if isinstance(values, (int, float, type(None))):
            values = [values]
        if isinstance(in_idx, (int, float, type(None))):
            in_idx = [in_idx]

        if len(values) != len(in_idx):
            raise IndexError("not as much values as infile indices")

        self.values += values
        self.in_idx += in_idx

        return len(values)


class CoordScanIn(CoordScan):
    """Coord used for scanning of a in coordinate.

    Only scan the first file found.
    All files are considered to have the same structure.

    Attribute
    ---------
    scanned: bool
        If the coord has been scanned
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, shared=False)

        self.scanned = False

    def scan_file(self, m, filename):
        """Scan file."""
        if not self.scanned:
            self.scan_file_values(filename)
            self.scanned = True


class CoordScanShared(CoordScan):
    """Coord used for scanning of a shared coordinate.

    Scan all files.

    Attribute
    ---------
    matchers: List of Matcher
    matches: List[List[str]]
        List of matches in the filename, for each file
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, shared=True)

        self.matchers = []
        self.matches = []

    @property
    def n_matchers(self):
        """Numbers of matchers for that coordinate."""
        return len(self.matchers)

    def add_matcher(self, matcher: Matcher):
        """Add a matcher."""
        self.matchers.append(matcher)

    def sort_values(self):
        """Sort by values."""
        self.matches = np.array(self.matches)

        order = super().sort_values()
        self.matches = self.matches[order]

    def slice(self, key):
        """Slice values."""
        self.matches = self.matches[key]
        super().slice(key)

    def scan_file(self, m, filename):
        """Scan file."""
        # Find matches
        matches = []
        for mchr in self.matchers:
            mchr.match = m.group(mchr.idx + 1)
            matches.append(mchr.match)

        # If they were not found before, which can happen when
        # there is more than one shared coord.
        if matches not in self.matches:
            n_values = self.scan_file_values(filename)

            matches = [matches for _ in range(n_values)]
            self.matches += matches


def get_coordscan(filegroup, coord, shared):
    """Get the right CoordScan object derived from a Coord."""
    coord_type = type(coord)
    CoordScanRB = type("CoordScanRB", (CoordScan, coord_type), {})

    if shared:
        CoordScanType = type("CoordScanSharedRB",
                             (CoordScanShared, CoordScanRB), {})
    else:
        CoordScanType = type("CoordScanInRB",
                             (CoordScanIn, CoordScanRB), {})

    return CoordScanType(filegroup, coord)


def reverse_slice(sl, size):
    """Reverse a slice."""
    ind = sl.indices(size)
    start = ind[1] - 1
    stop = ind[0]
    step = -1

    if stop == 0:
        stop = None
    else:
        stop -= 1

    return slice(start, stop, step)
