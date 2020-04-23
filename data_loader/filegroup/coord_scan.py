"""This is where the scanning is happening.

Handles scanning of the filenames, and of the
coordinate values inside files.

See :doc:`../scanning` and :doc:`../coord`.
"""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


import logging

import numpy as np

from data_loader.coordinates.coord import Coord
from data_loader.filegroup.matcher import Matcher


log = logging.getLogger(__name__)


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
    name: str
        Name of the coordinate in file.

    Attributes
    ----------
    filegroup: FilegroupScan or subclass
        Corresponding filegroup.
    coord: Coord or subclass
        Parent coordinate object.
    shared: bool
        If the coordinate is shared accross files.

    values: List[float]
        Temporary list of values found for this coordinate.
    in_idx: List[int]
        List of the index for each value inside the files.

    scan: Dict[str, List[List[str], Callable, Dict]]
        What and how to scan.
        Keys can be 'manual': values and in-indices are manually set,
        'in': stuff is to find inside the file, 'filename': stuff is to find
        in the filename.
        The values are lists of length 3. The first element contains
        the things to scan (values or in-indices), the second the function
        to use, the third the keyword arguments to pass.
    scanned: bool
        If the coordinate has been scanned.

    scan_attr: bool
        If attributes are to be scanned.
    scan_attributes_func: Callable
        Function to scan for attributes.
    """
    def __init__(self, filegroup, coord, shared, name):
        self.filegroup = filegroup
        self.coord = coord

        self.shared = shared
        self.scan = {}
        self.scanned = False

        self.scan_attr = False
        self.scan_attributes_func = scan_attributes_default


        self.values = []
        self.in_idx = []

        self.force_idx_descending = False

        super().__init__(name=name, array=None, units=coord.units)

    def __str__(self):
        s = [super().__str__()]
        s.append(["In", "Shared"][self.shared])
        s.append("To scan: %s" % ', '.join(self.scan.keys()))
        if self.scanned:
            s.append("Scanned")
        else:
            s.append("Not scanned")
        if len(self.in_idx) > 0:
            if all([c == self.in_idx[0] for c in self.in_idx]):
                s.append("In-file index is %s" % str(self.in_idx[0]))
        return '\n'.join(s)

    def set_values(self):
        """Set values."""
        self.values = np.array(self.values)
        self.in_idx = np.array(self.in_idx)
        self.sort_values()

    def assign_values(self):
        """Update parent coord with found values."""
        self.coord.update_values(self._array)

    def reset(self):
        """Remove values."""
        self.empty()
        self.values = []
        self.in_idx = []

    def sort_values(self):
        """Sort by values.

        Returns
        -------
        order: List[int]
            The order used to sort values.
        """
        order = np.argsort(self.values)
        self.values = self.values[order]
        self.in_idx = self.in_idx[order]

        return order

    def slice(self, key):
        self.in_idx = self.in_idx[key]
        self.values = self.values[key]
        if self.size is not None:
            super().slice(key)

    def get_in_idx(self, key):
        """Get the in file indices.

        Give the index inside the file corresponding to the
        demanded values.

        If the CS is empty and set as index descending, the key
        is mirrored.

        Parameters
        ----------
        key: Key
            Index of the demanded values.

        Returns
        -------
        key_data: List[int], Slice
        """
        try:
            if self.size is None:
                if self.force_idx_descending:
                    indices = mirror_key(key, self.coord.size)
                else:
                    indices = key.value
            else:
                indices = self.in_idx[key.value]

            key_data = key.__class__(indices)
        except:
            log.error("Error in retrieving in-file indices of '%s' for values %s.",
                      self.name, key)
            raise

        return key_data

    def is_to_scan(self) -> bool:
        """If the coord needs any kind of scanning."""
        out = ('in' in self.scan
               or 'filename' in self.scan)
        return out

    def is_to_check(self) -> bool:
        """If the coord values need to be checked."""
        out = (self.is_to_scan()
               or 'manual' in self.scan)
        return out

    def set_scan_filename_func(self, func, elts, **kwargs):
        """Set function for scanning values in filename.

        Parameters
        ----------
        func: Callable[[CoordScan, List[float]], [List[float], List[int]]]
        elts: List[str]
            Elements to scan ('values', 'in_idx')
        kwargs: Any

        See also
        --------
        scan_filename_default: for the function signature.
        """
        self.scan.pop('filename', None)
        self.scan['filename'] = [func, elts, kwargs]

    def set_scan_in_file_func(self, func, elts, **kwargs):
        """Set function for scanning values in file.

        Parameters
        ----------
        func: Callable[[CoordScan, file, List[float]], [List[float], List[int]]]
        elts: List[str]
            Elements to scan ('values', 'in_idx')
        kwargs: Any
       
        See also
        --------
        scan_in_file_default: for the function signature.
        """
        self.scan.pop('manual', None)
        self.scan.pop('in', None)
        self.scan['in'] = [func, elts, kwargs]

    def set_scan_manual(self, values, in_idx):
        """Set values manually.

        Parameters
        ----------
        values: List[float]
        in_idx: List[int]
        """
        self.scan.pop('manual', None)
        self.scan.pop('in', None)
        self.scan['manual'] = [None, ['values', 'in_idx'], {}]
        self.values = values
        self.in_idx = in_idx

    def set_scan_attributes_func(self, func):
        """Set function for scanning attributes in file.

        See also
        --------
        scan_attributes_default: for the function signature
        """
        self.scan_attr = True
        self.scan_attributes_func = func

    def scan_attributes(self, file):
        """Scan coordinate attributes if necessary.

        Using the user defined function.
        Apply them.
        """
        if self.scan_attr:
            attrs = self.scan_attributes_func(self, file)
            for name, value in attrs.items():
                self.set_attr(name, value)
            self.scan_attr = False

    def scan_values(self, file):
        """Find values for a file.

        Parameters
        ----------
        file:
            Object to access file.
            The file is already opened by FilegroupScan.open_file().

        Returns
        -------
        values: List[float]
            List of values found.

        Raises
        ------
        IndexError
            If not as many values as in file indices were found
        """
        values = None
        in_idx = None

        for to_scan, [func, elts, kwargs] in self.scan.items():
            if to_scan == 'manual':
                continue

            if to_scan == 'filename':
                log.debug("Scanning filename for '%s'", self.name)
                v, i = func(self, values, **kwargs)

            if to_scan == 'in':
                log.debug("Scanning in file for '%s'", self.name)
                v, i = func(self, file, values, **kwargs)

            if 'values' in elts:
                values = v
            if 'in_idx' in elts:
                in_idx = i

        if self.is_to_scan():
            if not isinstance(values, (list, tuple)):
                values = [values]
            if not isinstance(in_idx, (list, tuple)):
                in_idx = [in_idx]

            n_values = len(values)
            if n_values == 1:
                log.debug("Found value %s", values[0])
            else:
                log.debug("Found %s values between %s and %s",
                          n_values, values[0], values[-1])

            if n_values != len(in_idx):
                raise IndexError("Not as much values as infile indices. (%s)" % self.name)

            if 'manual' not in self.scan:
                self.values += values
                self.in_idx += in_idx

        return values


class CoordScanVar(CoordScan):
    """Coord used for scanning variables."""

    def set_values(self):
        self.values = np.array(self.values)
        self.in_idx = np.array(self.in_idx)

    def sort_values(self):
        order = range(list(self.size))
        return order


class CoordScanIn(CoordScan):
    """Coord used for scanning of a 'in' coordinate.

    Only scan the first file found.
    All files are thus considered to have the same structure.

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
            self.scan_values(file)
            self.scanned = True

    def is_to_open(self) -> bool:
        """If a file is to be open for scanning."""
        to_open = ((not self.scanned and 'in' in  self.scan)
                   or self.scan_attr)
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
    matches: Array[str]
        List of matches in the filename, for each file.
    """

    def __init__(self, *args, **kwargs):
        self.matchers = []
        self.matches = []

        super().__init__(*args, **kwargs, shared=True)

    def __str__(self):
        s = [super().__str__()]
        s.append('Matchers:')
        s += ['\t%s' % str(m) for m in self.matchers]
        return '\n'.join(s)

    @property
    def n_matchers(self) -> int:
        """Numbers of matchers for that coordinate."""
        return len(self.matchers)

    def add_matcher(self, matcher: Matcher):
        """Add a matcher."""
        self.matchers.append(matcher)

    def set_values(self):
        self.matches = np.array(self.matches)
        super().set_values()

    def sort_values(self):
        order = super().sort_values()
        self.matches = self.matches[order]
        return order

    def reset(self):
        super().reset()
        self.matches = []

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

        # If multiple coords, this match could have been found
        if matches not in self.matches:
            values = self.scan_values(file)
            if values is None:
                raise RuntimeError("'%s' has no scanning functions set." % self.name)
            if 'manual' in self.scan:
                for v in values:
                    i = self.get_index(v)
                    self.matches[i] = matches
            else:
                self.matches += [matches for _ in range(len(values))]

    def is_to_open(self) -> bool:
        """If the file must be opened for scanning."""
        to_open = ('in' in self.scan or self.scan_attr)
        return to_open


def get_coordscan(filegroup, coord, shared, name):
    """Get the right CoordScan object derived from a Coord.

    Dynamically create a subclass of CoordScanShared
    or CoordScanIn, that inherits methods from a
    subclass of Coord.

    Parameters
    ----------
    filegroup: FilegroupScan
    coord: Coord or subclass
        Coordinate to create a CoordScan object from.
    shared: bool
        If the coordinate is shared.
    name: str
        Name of the coordinate in file.
    """
    coord_type = type(coord)
    if coord.name == 'var':
        coordscan_type = CoordScanVar
    else:
        coordscan_type = CoordScan
    CoordScanRB = type("CoordScanRB", (coordscan_type, coord_type), {})

    if shared:
        CoordScanType = type("CoordScanSharedRB",
                             (CoordScanShared, CoordScanRB), {})
    else:
        CoordScanType = type("CoordScanInRB",
                             (CoordScanIn, CoordScanRB), {})

    return CoordScanType(filegroup, coord, name=name)


def mirror_key(key, size):
    """Mirror indices in a key."""
    if key.type == 'int':
        value = size - key.value - 1
    elif key.type in ['list', 'slice']:
        key.parent_size = size
        value = [size - z - 1 for z in key.tolist()]
    return value


def scan_filename_default(cs, values, **kwargs):
    """Scan filename to find values.

    Matches found by the regex are accessible from
    the matchers objects in the CoordScan object passed
    to the function (as cs).
    Do not forget the function needs a CoordScan in
    first argument !

    Parameters
    ----------
    cs: CoordScan
    values: List[float]
        Values found previously in the same file by
        in-file scanning.
    kwargs
        Static keywords arguments set by
        Constructor.set_scan_filename()

    Returns
    -------
    values: float, List[float]
        Values found.
    in_idx: int, None, List[int]
        In file indices found.

    Notes
    -----
    See scan_library for various examples.
    """
    raise NotImplementedError()


def scan_in_file_default(cs, file, values, **kwargs):
    """Scan values and in-file indices inside file.

    Scan file to find values and in-file indices.

    Parameters
    ----------
    cs: CoordScan
    file:
        Object to access file.
        The file is already opened by FilegroupScan.open_file().
    values: List[float]
        Values found previously in filename.
    kwargs
        Static keywords arguments set by
        Constructor.set_scan_in_file()

    Returns
    -------
    values: List[float]
        Values found in file
    in_idx: List[int]
        Indices of values in file

    Notes
    -----
    See scan_library for various examples.
    scan_in_file_nc() for instance.
    """
    raise NotImplementedError()


def scan_attributes_default(cs, file):
    """Scan coordinate attributes.

    Attributes are set to the CoordScan by
    cs.set_attr().

    Parameters
    ----------
    cs: CoordScan
    file:
        Object to access file.
        The file is already opened by FilegroupScan.open_file().

    Returns
    -------
    attributes: Dict
        Attributes.
        {'name': value}
    """
    raise NotImplementedError()
