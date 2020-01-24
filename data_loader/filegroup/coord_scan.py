"""Coordinate scanning.

Handles scanning of the filenames, and of the
coordinate values inside files.
"""

import logging
from types import MethodType

import numpy as np

from data_loader.coordinates.coord import Coord
from data_loader.key import Key


log = logging.getLogger(__name__)


class Matcher():
    """Object associated with a matcher in the pre-regex.

    Holds (temporarily) the match for the current file.

    Parameters
    ----------
    m: re.match
        Match object of a matcher in the pre-regex.
        See FilegroupScan.scan_pregex().
    idx: int
        Index of the matcher in the full pre-regex

    Attributes
    ----------
    coord: str
        Coordinate name.
    idx: int
        Matcher index in the full pre-regex.
    elt: str
        Coordinate element.
    dummy: bool
        If the matcher is a dummy, ie not containing any
        information, or redondant information.
    ELT_RGX: Dict
        Regex str for each type of element.
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

    def __str__(self):
        s = '{0}:{1}, idx={2}'.format(self.coord, self.elt, self.idx)
        if self.dummy:
            s += ', dummy'
        return s


class CoordScan(Coord):
    """Abstract Coord used for scanning of one variable.

    Parameters
    ----------
    filegroup: Filegroup
        Corresponding filegroup.
    coord: Coord
        Parent coordinate.
    shared: bool
        If the coordinate is shared accross files.

    Attributes
    ----------
    filegroup: FilegroupLoad or subclass
        Corresponding filegroup.
    coord: Coord
        Parent coordinate object.
    shared: bool
        If the coordinate is shared accross files.
    values: List[float]
        Temporary list of values found for this coordinate.
    in_idx: List[int]
        List of the index for each value inside the files.
    scan: set
        What part of the file is to be scanned.
        { in | filename | manual | attributes } or a combination of the three
    scanned: bool
        If the coordinate has been scanned.
    scan_filename_kwargs: Dict
        Keyword arguments to pass to the scan_filename function.
    scan_in_file_kwargs: Dict
        Keyword arguments to pass to the scan_in_file function.
    """

    def __init__(self, filegroup, coord: Coord, shared: bool):
        self.filegroup = filegroup
        self.coord = coord

        self.shared = shared
        self.scan = set()
        self.scanned = False

        self.values = []
        self.in_idx = []

        self.scan_filename_kwargs = {}
        self.scan_in_file_kwargs = {}

        self._idx_descending = False

        super().__init__(coord.name, coord._array, coord.units, coord.name_alt)

    def __str__(self):
        s = [super().__str__()]
        s.append(["In", "Shared"][self.shared])
        s.append("To scan: %s" % str(self.scan))
        if self.scanned:
            s.append("Scanned")
            s.append("Found %d values, kept %d" % (len(self.values), self.size))
            if all([c == self.in_idx[0] for c in self.in_idx]):
                s.append("In-file index is %s" % str(self.in_idx[0]))
        else:
            s.append("Not scanned")
        return '\n'.join(s)

    def is_idx_descending(self):
        """Is idx descending.

        Meaning the in-file index are decreasing
        when values are increasing.
        """
        return self._idx_descending

    def set_values(self, values):
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

    def get_in_idx(self, key):
        """Get the in file indices.

        Give the index inside the file corresponding to the
        demanded values.

        Parameters
        ----------
        key: Key
            Index of the demanded values.

        Returns
        -------
        key_data: List[int] or Slice
        """
        if self.size is None:
            key_data = key
            if self.is_idx_descending():
                key_data.reverse(self.size)
        else:
            key_data = Key(self.in_idx[key.value])

        return key_data

    def is_to_open(self):
        """Return if the coord needs to open the current file."""
        raise NotImplementedError

    def scan_filename(self, **kwargs): # pylint: disable=method-hidden
        """Scan filename to find values.

        Matches found by the regex are accessible from
        the matchers objects in the CoordScan object passed
        to the function (as self).
        Do not forget the function needs a CoordScan in
        first argument !

        Parameters
        ----------
        kwargs
            Static keywords arguments set by
            Constructor.set_scan_filename_func()

        Returns
        -------
        values: List[float]
            Values found.

        Raises
        ------
        NotImplementedError
            If scan_filename was not set.

        Notes
        -----
        See scan_library for various examples.
        get_date_from_matches() for instance.
        """
        raise NotImplementedError("scan_filename was not set for '%s'" % self.name)

    def scan_in_file(self, file, values, **kwargs): # pylint: disable=method-hidden
        """Scan values and in-file indices inside file.

        Scan file to find values and in-file indices.

        Parameters
        ----------
        file:
            Object to access file.
            The file is already opened by FilegroupScan.open_file().
        values: List[float]
            Values found previously in filename.
        kwargs
            Static keywords arguments set by
            Constructor.set_scan_in_file_func()

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

        Notes
        -----
        See scan_library for various examples.
        scan_in_file_nc() for instance.
        """
        raise NotImplementedError("scan_in_file was not set for '%s" % self.name)

    def scan_attributes(self, file): #pylint: disable=method-hidden
        """Scan coordinate attributes.

        Only `units` attribute supported for now.

        Parameters
        ----------
        file:
            Object to access file.
            The file is already opened by FilegroupScan.open_file().

        Returns
        -------
        attributes: Dict
            Attributes.
            {'name': value}

        Raises
        ------
        NotImplementedError
            If scan_attribute was not set.
        """
        raise NotImplementedError("scan_attributes was not set for '%s" % self.name)

    def set_scan_filename_func(self, func, **kwargs):
        """Set function for scanning values.

        See CoordScan.scan_filename()
        and Constructor.set_scan_filename_func()
        """
        self.scan.add("filename")
        self.scan_filename = MethodType(func, self)
        self.scan_filename_kwargs = kwargs

    def set_scan_in_file_func(self, func, **kwargs):
        """Set function for scanning values in file.

        See CoordScan.scan_in_file()
        and Constructor.set_scan_in_file_func()
        """
        self.scan.add("in")
        self.scan_in_file = MethodType(func, self)
        self.scan_in_file_kwargs = kwargs

    def set_scan_manual(self, values, in_idx):
        """Set values manually.

        Parameters
        ----------
        values: List[float]
        in_idx: List[int]
        """
        self.scan.discard('in')
        self.scan.discard('filename')
        self.scan.add('manual')
        self.set_values(values)
        self.in_idx = in_idx

    def set_scan_attributes(self, func):
        """Set function for scanning attributes in file.

        See CoordScan.scan_attributes()
        and Constructor.set_scan_coords_attributes()
        """
        self.scan.add("attributes")
        self.scan_attributes = MethodType(func, self)

    def scan_file_values(self, file):
        """Find values for a file.

        Parameters
        ----------
        file:
            Object to access file.
            The file is already opened by FilegroupScan.open_file().

        Returns
        -------
        n_values: int
            Number of values found

        Raises
        ------
        IndexError
            If not as many values as in file indices were found
        """
        values = None
        in_idx = None
        if 'attributes' in self.scan and not self.scanned:
            log.debug("Scanning attributes in file for '%s'", self.name)
            attributes = self.scan_attributes(file) #pylint: disable=not-callable
            for name, attr in attributes.items():
                if attr is not None:
                    self.coord.__setattr__(name, attr)

        if 'filename' in self.scan:
            values = self.scan_filename(**self.scan_filename_kwargs) # pylint: disable=not-callable
            log.debug("Scanning filename for '%s'", self.name)

        if 'in' in self.scan:
            log.debug("Scanning in file for '%s'", self.name)
            values, in_idx = self.scan_in_file(file, values, # pylint: disable=not-callable
                                               **self.scan_in_file_kwargs)

        if isinstance(values, (int, float, type(None))):
            values = [values]
        if isinstance(in_idx, (int, float, type(None))):
            in_idx = [in_idx]

        n_values = len(values)
        if n_values == 1:
            log.debug("Found value %s", values[0])
        else:
            log.debug("Found %s values between %s and %s",
                      n_values, values[0], values[n_values-1])

        if n_values != len(in_idx):
            raise IndexError("not as much values as infile indices")

        self.values += values
        self.in_idx += in_idx
        self.scanned = True

        return n_values


class CoordScanIn(CoordScan):
    """Coord used for scanning of a 'in' coordinate.

    Only scan the first file found.
    All files are considered to have the same structure.

    Parameters
    ----------
    Passed to CoordScan(), minus `shared`.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, shared=False)

    def scan_file(self, m, file):
        """Scan file.

        Parameters
        ----------
        m: re.match
            Match of the filename against the regex.
        file:
            Object to access file.
            The file is already opened by FilegroupScan.open_file().
        """
        if not self.scanned:
            self.scan_file_values(file)

    def is_to_open(self):
        to_open = False
        if 'in' in self.scan and not self.scanned:
            to_open = True
        if 'attributes' in self.scan and not self.scanned:
            to_open = True
        return to_open


class CoordScanShared(CoordScan):
    """Coord used for scanning of a 'shared' coordinate.

    Scan all files.

    Parameters
    ----------
    Passed to CoordScan(), minus `shared`.

    Attributes
    ----------
    matchers: List[Matcher]
        Matcher objects corresponding to this coordinate.
    matches: List[List[str]]
        List of matches in the filename, for each file
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, shared=True)

        self.matchers = []
        self.matches = []

    def __str__(self):
        s = [super().__str__()]
        s.append('Matchers:')
        s += ['\t%s' % str(m) for m in self.matchers]
        return '\n'.join(s)
    @property
    def n_matchers(self):
        """Numbers of matchers for that coordinate."""
        return len(self.matchers)

    def add_matcher(self, matcher: Matcher):
        """Add a matcher."""
        self.matchers.append(matcher)

    def sort_values(self):
        self.matches = np.array(self.matches)

        order = super().sort_values()
        self.matches = self.matches[order]

    def slice(self, key):
        self.matches = self.matches[key]
        super().slice(key)

    def scan_file(self, m, file):
        """Scan file.

        Parameters
        ----------
        m: re.match
            Match of the filename against the regex.
        file:
            Object to access file.
            The file is already opened by FilegroupScan.open_file().
        """
        # Find matches
        matches = []
        for mchr in self.matchers:
            mchr.match = m.group(mchr.idx + 1)
            matches.append(mchr.match)

        log.debug("Found matches %s for filename %s", matches, m.group())

        # If they were not found before, which can happen when
        # there is more than one shared coord.
        if matches not in self.matches:
            n_values = self.scan_file_values(file)

            matches = [matches for _ in range(n_values)]
            self.matches += matches

    def is_to_open(self):
        to_open = False
        to_open = to_open or ('in' in self.scan)
        to_open = to_open or ('attributes' in self.scan and not self.scanned)
        return to_open


def get_coordscan(filegroup, coord, shared):
    """Get the right CoordScan object derived from a Coord.

    Parameters
    ----------
    filegroup: FilegroupScan
    coord: Coord or subclass
        Coordinate to create a CoordScan object from.
    shared: bool
        If the coordinate is shared.
    """
    coord_type = type(coord)
    CoordScanRB = type("CoordScanRB", (CoordScan, coord_type), {})

    if shared:
        CoordScanType = type("CoordScanSharedRB",
                             (CoordScanShared, CoordScanRB), {})
    else:
        CoordScanType = type("CoordScanInRB",
                             (CoordScanIn, CoordScanRB), {})

    return CoordScanType(filegroup, coord)

