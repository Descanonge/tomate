"""Coordinate scanning.

Handles scanning of the filenames, and of the
coordinate values inside files.

Contains
--------

CoordScan:
    Abstract class, handles scanning for a
    given variable.
    Each object is parented to a Coord so that
    once scanned, the values can be transferred.

CoordScanInOut:
    The values are contained either
    solely in the filename ("out")
    in the filename and in the file ("inout")

CoordScanIn:
    The values are fully contained in the file ("in")
"""

from types import MethodType
from typing import List

import numpy as np

from data_loader.stubs import NpIdx
from data_loader.coord import Coord


class Matcher():
    """Object associated with a matcher.

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
               "mm": r"\d+\d",
               "D": r"[a-zA-Z]*",
               "dd": r"\d+\d",
               "doy": r"\d+\d+\d",
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
    inout: str
        inout flag

    Attributes
    ----------
    coord: Coord
        parent coordinate object
    inout: str
        inout flag
    values: List[float]
        list of values found for this coordinate
    slice_total: Slice
        Slice that is used (migth be less that what is available
        on disk)
    """

    def __init__(self, filegroup, CSRB, coord: Coord, inout: str):
        self.filegroup = filegroup
        self.coord = coord
        self.inout = inout
        self.values = []
        self._size_total = None
        self.slice_total = slice(None, None)

        super(CSRB, self).__init__(coord.name, coord._array, coord.unit, coord.name_alt)

    def set_values(self, values: List):
        """Manually set values"""
        self.values = values

    def assign_values(self):
        """Update parent coord with found values."""
        self.coord.update_values(self._array)
        self._size_total = self._size

    def sort_values(self):
        """Sort by values."""
        order = np.argsort(self.values)
        self.values = np.array(self.values)
        self.values = self.values[order]

    def get_slice(self, key):
        # TODO: doc
        """Return key of what is available.

        Parameters
        ----------
        key: Slice or List[int]
        """
        if isinstance(key, slice):
            try:
                start, stop, step = key.indices(self.size)
            except TypeError:
                key_data = slice(None, None)
            else:
                key_data = slice(start + self.slice_total.start,
                                 stop + self.slice_total.start,
                                 step)

        if isinstance(key, list):
            key_data = [z + self.slice_total.start for z in key]

        return key_data


class CoordScanInOut(CoordScan):
    """Abstract Coord used for scanning of one variable.

    Keep list of values, and on the same index, the matches
    for the filenames, and the index inside the file.
    (No index inside the file is noted as None)

    Parameters
    ----------
    filegroup: Filegroup
        Corresponding filegroup
    coord: Coord
        Parent coordinate object
    inout: str
        inout flag

    Attributes
    ----------
    matches: List[str]
        matches found in filenames
    in_idx: List[int]
        list of index in files
    matchers: List[Matcher]
        matchers for this coordinate
    """

    def __init__(self, filegroup, CSRB, coord: Coord, inout: str):
        super(type(self), self).__init__(filegroup, CSRB, coord, inout)

        self.matches = []
        self.in_idx = []
        self.matchers = []

    @property
    def n_matchers(self):
        """Number of matchers"""
        return len(self.matchers)

    def add_matcher(self, matcher: Matcher):
        """Add a matcher."""
        self.matchers.append(matcher)

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
        raise NotImplementedError("scan_filename was not set for ({self.name})")

    def scan_in_file(self, filename, values): # pylint: disable=method-hidden
        """Scan values in file.

        Scan file `filename` for `values`

        Parameters
        ----------
        filename: str
            filename
        values: List[float]
            Values found previously in filename

        Returns
        -------
        values: List[float]
            Values found in file
        in_idx: List[int]
            Indices of values in file
        """
        return values, None

    def set_scan_filename_func(self, func):
        """Set function for scanning values.

        Parameters
        ----------
        func: Callable[[CoordScan, re.match], values: List[float]]
            Function that recover values from filename
        """
        self.scan_filename = MethodType(func, self)

    def set_scan_in_file_func(self, func):
        """Set function for scanning values in file.

        Parameters
        ----------
        func: Callable[[CoordScan, filename: str, values: List[float]],
                       values: List[float], in_idx: List[int]]
        """
        self.scan_in_file = MethodType(func, self)

    def scan_file(self, m, filename):
        """Find values for a file.

        Parameters
        ----------
        m: re.match
            Match of the filename against the regex
        filename: str
            Filename
        """
        # Scan filename
        matches = []
        for mchr in self.matchers:
            mchr.match = m.group(mchr.idx+1)
            matches.append(mchr.match)

        if matches not in self.matches:

            values = self.scan_filename() # pylint: disable=not-callable
            values, in_idx = self.scan_in_file(filename, values) # pylint: disable=not-callable

            if isinstance(values, (int, float, type(None))):
                values = [values]
            if isinstance(in_idx, (int, float, type(None))):
                in_idx = [in_idx]

            if len(values) != len(in_idx):
                raise IndexError("not as much values as infile indices")

            matches = [matches for _ in range(len(values))]
            self.matches += matches
            self.values += values
            self.in_idx += in_idx

    def sort_values(self):
        """Sort by values."""
        self.values = np.array(self.values)
        self.matches = np.array(self.matches)
        self.in_idx = np.array(self.in_idx)

        order = np.argsort(self.values)
        self.values = self.values[order]
        self.matches = self.matches[order]
        self.in_idx = self.in_idx[order]

    def slice(self, key: NpIdx):
        """Slice values."""
        self.matches = self.matches[key]
        super(type(self), self).slice(key)


class CoordScanIn(CoordScan):
    """Abstract Coord used for scanning of one variable.

    Values are fully contained in files.
    Only the first file is scanned.

    Parameters
    ----------
    filegroup: Filegroup
        Corresponding filegroup
    coord: Coord
        Parent Coord object

    Attribute
    ---------
    scanned: bool
        If the coordinate has been scanned
    """

    def __init__(self, filegroup, CSRB, coord):
        inout = "in"
        super(type(self), self).__init__(filegroup, CSRB, coord, inout)

        self.scanned = False

    def scan_in_file(self, filename): # pylint: disable=method-hidden
        """Scan values in file.

        Parameters
        ----------
        filename: str
            Filename to scan

        Returns
        -------
        values: List[float]
            Values found in file

        Raises
        ------
        NotImplementedError
            If scan if file was not set.
        """
        raise NotImplementedError("scan_in_file was not set for {0}".format(self.name))

    def set_scan_in_file_func(self, func):
        """Set function for scanning values in file.

        Parameters
        ----------
        func: Callable[[CoordScan, filename: str], values: List[float]]
        """
        self.scan_in_file = MethodType(func, self)

    def scan_file(self, m, filename):
        """Find values for a filename.

        Parameters
        ----------
        m: re.match
            Match of the filename against the regex
        filename: str
            Filename
        """
        if not self.scanned:
            values = self.scan_in_file(filename) # pylint: disable=not-callable

            if isinstance(values, (int, float, type(None))):
                values = [values]

            self.values = values

        self.scanned = True
