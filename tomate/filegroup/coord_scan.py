"""This is where the scanning is happening.

Handles scanning of the filenames, and of the
coordinate values inside files.

See :doc:`../scanning` and :doc:`../coord`.
"""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Tuple, Union
import re

import numpy as np

from tomate.coordinates.coord import Coord

from tomate.custom_types import File, KeyLike, KeyLikeInt
from tomate.filegroup.matcher import Matcher
from tomate.keys.key import Key

if TYPE_CHECKING:
    from tomate.filegroup.filegroup_load import FilegroupLoad


log = logging.getLogger(__name__)


class CoordScan(Coord):
    """Abstract Coord used for scanning of one variable.

    :param filegroup: Corresponding filegroup.
    :param coord: Parent coordinate.
    :param shared: If the coordinate is shared accross files.
    :param name: Name of the coordinate in file.

    :attr filegroup: FilegroupLoad: Corresponding filegroup.
    :attr coord: Coord: Parent coordinate object.
    :attr shared: bool: If the coordinate is shared accross files.
    :attr contains: Optional[np.ndarray]:
        For each value of the available scope, the index of the
        corresponding value in that CS.
        If that value is not contained in this filegroup, the
        index is None.

    :attr values: Union[List, np.ndarray]: Temporary list of values found
        for this coordinate.
    :attr in_idx: Union[List, np.ndarray]: List of the index for each value
        inside the files.

    :attr scan: Dict[str, List[Callable, List[str], Dict]]:
        What and how to scan.
        Keys can be 'manual': values and in-indices are manually set,
        'in': stuff is to find inside the file, or 'filename': stuff is to find
        in the filename.
        The values are lists of length 3. The first element contains
        the things to scan (values or in-indices), the second the function
        to use, the third the keyword arguments to pass.
    :attr scanned: bool: If the coordinate has been scanned.

    :attr scan_attr: bool: If attributes are to be scanned.
    :attr scan_attributes_func: Callable: Function to scan for attributes.
    """
    def __init__(self, filegroup: 'FilegroupLoad',
                 coord: Coord, *,
                 shared: bool = False,
                 name: str = None):
        super().__init__(name=name, array=None, units=coord.units)

        self.filegroup = filegroup
        self.coord = coord
        self.contains = None

        self.shared = shared
        self.scan = {}
        self.scanned = False

        self.scan_attr = False
        self.scan_attributes_func = None

        self.change_units_custom = None

        self.values = []
        self.in_idx = []

        self.force_idx_descending = False

    def __repr__(self):
        s = [super().__repr__()]
        s.append(["In", "Shared"][self.shared])
        s.append("To scan: {}".format(', '.join(self.scan.keys())))
        if self.scanned:
            s.append("Scanned")
        else:
            s.append("Not scanned")
        if len(self.in_idx) > 0:
            if all([c == self.in_idx[0] for c in self.in_idx]):
                s.append("In-file index is {}".format(str(self.in_idx[0])))
        return '\n'.join(s)

    def set_values(self):
        """Set values."""
        self.values = np.array(self.values)
        self.in_idx = np.array(self.in_idx)
        self.sort_values()

    def reset(self):
        """Remove values."""
        self.empty()
        self.values = []
        self.in_idx = []

    def sort_values(self) -> np.ndarray:
        """Sort by values.

        :returns: The order used to sort values.
        """
        order = np.argsort(self.values)
        self.values = self.values[order]
        self.in_idx = self.in_idx[order]

        return order

    def slice(self, key: KeyLikeInt):
        self.in_idx = self.in_idx[key]
        self.values = self.values[key]
        if self.size is not None:
            super().slice(key)

    def slice_from_avail(self, key: KeyLikeInt) -> bool:
        """Slice using a key working on available scope.

        Use `contains` attribute to convert.
        Returns true if there was a change in number
        of value. False otherwise.
        """
        indices = self.contains[key]
        indices = np.delete(indices,
                            np.where(np.equal(indices, None))[0])
        out = False
        if indices.size != self.size:
            out = True
        self.slice(indices.astype(int))
        return out

    def get_in_idx(self, key: KeyLike) -> Key:
        """Get the in file indices.

        Give the index inside the file corresponding to the
        demanded values.

        If the CS is empty and set as index descending, the key
        is mirrored.

        :param key: Index of the demanded values.
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
        except Exception:
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

    def set_scan_filename_func(self, func: Callable, elts: List[str], **kwargs: Any):
        """Set function for scanning values in filename.

        :param elts: Elements to scan ('values', 'in_idx')
        :param kwargs: [opt]

        See also
        --------
        scan_filename_default: for the function signature.
        """
        self.scan.pop('filename', None)
        self.scan['filename'] = [func, elts, kwargs]

    def set_scan_in_file_func(self, func: Callable, elts: List[str], **kwargs: Any):
        """Set function for scanning values in file.

        :param elts: Elements to scan ('values', 'in_idx')
        kwargs: [opt]

        See also
        --------
        scan_in_file_default: for the function signature.
        """
        self.scan.pop('manual', None)
        self.scan.pop('in', None)
        self.scan['in'] = [func, elts, kwargs]

    def set_scan_manual(self, values: np.ndarray, in_idx: np.ndarray):
        """Set values manually."""
        self.scan.pop('manual', None)
        self.scan.pop('in', None)
        self.scan['manual'] = [None, ['values', 'in_idx'], {}]
        self.values = values
        self.in_idx = in_idx

    def set_scan_attributes_func(self, func: Callable):
        """Set function for scanning attributes in file.

        See also
        --------
        scan_attributes_default: for the function signature
        """
        self.scan_attr = True
        self.scan_attributes_func = func

    def scan_attributes(self, file: File):
        """Scan coordinate attributes if necessary.

        Using the user defined function.
        Apply them.
        """
        if self.scan_attr:
            attrs = self.scan_attributes_func(self, file)
            log.debug("Found coordinates attributes %s", list(attrs.keys()))
            for name, value in attrs.items():
                self.set_attr(name, value)
            self.scan_attr = False

    def scan_values(self, file: File):
        """Find values for a file.

        :param file: Object to access file.
            The file is already opened by FilegroupScan.open_file().

        :param Returns: List of values found.

        :raises IndexError: If not as many values as in file indices were found
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
                raise IndexError("Not as much values as infile indices."
                                 f"({self.name})")

            if 'manual' not in self.scan:
                self.values += values
                self.in_idx += in_idx

        return values

    def find_contained(self, outer: np.ndarray) -> List[Union[int, None]]:
        """Find values of inner contained in outer.

        :param outer: List of values.

        :returns:  List of the index of the outer values in the CS.
            If the value is not contained in CS, the index is `None`.
        """
        if self.size is None:
            contains = np.arange(len(outer))
        else:
            contains = []
            for value in outer:
                contains.append(
                    self.get_index_exact(value))
            contains = np.array(contains)
        self.contains = contains


class CoordScanVar(CoordScan):
    """Coord used for scanning variables."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = kwargs.pop('name', '')

    def set_values(self):
        self.values = np.array(self.values)
        self.in_idx = np.array(self.in_idx)

    def sort_values(self) -> np.ndarray:
        order = range(list(self.size))
        return order


class CoordScanIn(CoordScan):
    """Coord used for scanning of a 'in' coordinate.

    Only scan the first file found.
    All files are thus considered to have the same structure.
    """
    def __init__(self, *args, **kwargs):
        kwargs.pop('shared', None)
        super().__init__(*args, **kwargs, shared=False)

    def scan_file(self, m: re.match, file: File):
        """Scan file.

        :param m: Match of the filename against the regex.
        :param file: Object to access file.
            The file is already opened by FilegroupScan.open_file().
        """
        if not self.scanned:
            self.scan_values(file)
            self.scanned = True

    def is_to_open(self) -> bool:
        """If a file is to be open for scanning."""
        to_open = ((not self.scanned and 'in' in self.scan)
                   or self.scan_attr)
        return to_open


class CoordScanShared(CoordScan):
    """Coord used for scanning of a 'shared' coordinate.

    Scan all files.

    :attr matchers: List[Matcher]: Matcher objects for this coordinate.
    :attr matches: Array[str]: List of matches in the filename, for each file.
    """

    def __init__(self, *args, **kwargs):
        kwargs.pop('shared', None)
        super().__init__(*args, **kwargs, shared=True)

        self.matchers = []
        self.matches = []

    def __repr__(self):
        s = [super().__repr__()]
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

    def sort_values(self) -> np.ndarray:
        order = super().sort_values()
        self.matches = self.matches[order]
        return order

    def reset(self):
        super().reset()
        self.matches = []

    def slice(self, key: Union[List[int], slice]):
        self.matches = self.matches[key]
        super().slice(key)

    def scan_file(self, m: re.match, file: File):
        """Scan file.

        :param m: Match of the filename against the regex.
        :param file: Object to access file.
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


def get_coordscan(filegroup: 'FilegroupLoad', coord: Coord,
                  shared: bool, name: str):
    """Get the right CoordScan object derived from a Coord.

    Dynamically create a subclass of CoordScanShared
    or CoordScanIn, that inherits methods from a
    subclass of Coord.

    :param coord: Coordinate to create a CoordScan object from.
    :param shared: If the coordinate is shared.
    :param name: Name of the coordinate in file.
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


def mirror_key(key: Key, size: int) -> KeyLike:
    """Mirror indices in a key."""
    if key.type == 'int':
        value = size - key.value - 1
    elif key.type in ['list', 'slice']:
        key.parent_size = size
        value = [size - z - 1 for z in key.tolist()]
    return value


def scan_filename_default(cs: CoordScan, values: List[float] = None,
                          **kwargs: Any) -> Tuple[Union[Any, List[Any]]]:
    """Scan filename to find values.

    Matches found by the regex are accessible from
    the matchers objects in the CoordScan object passed
    to the function (as cs).
    Do not forget the function needs a CoordScan in
    first argument !

    :param values: Values (eventually) found previously in the same file by
        in-file scanning. Is None otherwise.
    :param kwargs: [opt] Static keywords arguments set by
        Constructor.set_scan_filename()

    Returns
    :param values: Values found. Type should correspond to the Coordinate.
        Can be a single value or a list.
    :param in_idx: Indices of found values in the file.
        Can be any type (or a list of same length as `values`).
        A None index indicates the file does not have the corresponding
        dimension (it has been squeezed).

    Notes
    -----
    See scan_library for various examples.
    """
    raise NotImplementedError()


def scan_in_file_default(cs: CoordScan, file: File, values: List[float] = None,
                         **kwargs: Any) -> Tuple[Union[Any, List[Any]]]:
    """Scan values and in-file indices inside file.

    Scan file to find values and in-file indices.

    :param file: Object to access file.
        The file is already opened by FilegroupScan.open_file().
    :param values: Values (eventually) found previously in filename.
        Is None otherwise.
    :param kwargs: Static keywords arguments set by
        Constructor.set_scan_in_file()

    :param values: Values found. Type should correspond to the Coordinate.
        Can be a single value or a list.
    :param in_idx: Indices of found values in the file.
        Can be any type (or a list of same length as `values`).
        A None index indicates the file does not have the corresponding
        dimension (it has been squeezed).

    Notes
    -----
    See scan_library for various examples.
    scan_in_file_nc() for instance.
    """
    raise NotImplementedError()


def scan_attributes_default(cs: CoordScan, file: File) -> Dict[str, Any]:
    """Scan coordinate attributes.

    Attributes are set to the CoordScan by
    cs.set_attr().

    :param file: Object to access file.
        The file is already opened by FilegroupScan.open_file().

    :returns: Attributes {'name': value}.
    """
    raise NotImplementedError()
