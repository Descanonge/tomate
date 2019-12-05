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
               "mm": r"\d?\d",
               "D": r"[a-zA-Z]*",
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
        inout flag

    Attributes
    ----------
    coord: Coord
        parent coordinate object
    shared: str
        If the coordinate is shared accross files
    values: List[float]
        list of values found for this coordinate
    scan: set
        What is to be scanned
    """

    def __init__(self, filegroup, coord: Coord, shared: bool):
        self.filegroup = filegroup
        self.coord = coord

        self.shared = shared
        self.scan = set()

        self.values = []
        self.in_idx = []

        super().__init__(coord.name, coord._array, coord.unit, coord.name_alt)

    def set_values(self, values: List):
        """Manually set values"""
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

        return order

    def get_in_idx(self, key):
        # TODO: doc
        """Return key of what is available.

        Parameters
        ----------
        key: Slice or List[int]
        """
        # TODO: input info on descending manually
        if self.size is None:
            key_data = key
        else:
            key_data = self.in_idx[key]

        if isinstance(key_data, (list, np.ndarray)):
            diff = np.diff(key_data)
            if np.all(diff == 1):
                key_data = slice(key_data[0], key_data[-1]+1, 1)
            elif np.all(diff == -1):
                key_data = slice(key_data[-1], key_data[0]+1, -1)

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
        raise NotImplementedError("scan_in_file was not set for %s" % self.name)

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

    def set_scan_manual(self, values):
        """Set values manually."""
        self.scan = set(['manual'])
        self.set_values(values)

    def scan_file_values(self, m, filename):
        """Find values for a file.

        Parameters
        ----------
        m: re.match
            Match of the filename against the regex
        filename: str
            Filename
        """
        values = None
        in_idx = None
        if 'filename' in self.scan:
            values = self.scan_filename(m) # pylint: disable=not-callable
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
            self.scan_file_values(m, filename)
            self.scanned = True

class CoordScanShared(CoordScan):
    """Coord used for scanning of a shared coordinate.

    Attribute
    ---------
    matchers: List of Matcher
    matchers: ?
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
        matches = []
        for mchr in self.matchers:
            mchr.match = m.group(mchr.idx + 1)
            matches.append(mchr.match)

        if matches not in self.matches:
            n_values = self.scan_file_values(m, filename)

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
