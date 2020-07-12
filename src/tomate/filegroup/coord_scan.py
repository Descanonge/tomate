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
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Tuple, Union
import re

import numpy as np

from tomate.coordinates.coord import Coord

from tomate.custom_types import File, KeyLike, KeyLikeInt
from tomate.filegroup.matcher import Matcher
from tomate.keys.key import Key

if TYPE_CHECKING:
    from tomate.filegroup.filegroup_load import FilegroupLoad


log = logging.getLogger(__name__)


@dataclass
class CoordScanSpec:
    coord: Union[str, Coord]
    shared: Union[str, bool] = 'in'
    name: str = None

    def process(self, dims: Union[Coord] = None):
        if isinstance(self.shared, str):
            self.shared = {'in': False, 'shared': True}[self.shared]

        if isinstance(self.coord, str):
            try:
                self.coord = dims[self.coord]
            except KeyError:
                raise KeyError("'{}' is not in dimensions.".format(self.coord))
        if self.name is None:
            self.name = self.coord.name

    def __iter__(self):
        return iter([self.coord, self.shared, self.name])


class Scanner:
    def __init__(self, kind, func, **kwargs):
        self.kind = kind
        self.func = func
        self.kwargs = kwargs
        self.to_scan = True

    def __call__(self, *args, **kwargs):
        return self.func(*args, **self.kwargs)

    def scan(self, *args):
        self.to_scan = False
        return self(*args, **self.kwargs)

    def copy(self):
        return self.__class__(self.kind, self.func, **self.kwargs.copy())

    @property
    def name(self) -> str:
        try:
            name = self.func.__name__
        except AttributeError:
            name = ''
        return name

    def __bool__(self):
        return self.to_scan

    def __repr__(self):
        s = ' - '.join([self.kind, self.func.__name__])
        return s


class ScannerCS(Scanner):
    def __init__(self, kind, func, elts, **kwargs):
        self.kind = kind
        self.func = func
        self.elts = elts
        self.kwargs = kwargs
        self.to_scan = True
        self.restrain = None

    @property
    def returns(self) -> List[str]:
        """Elements returned by the scanner."""
        if self.restrain is not None:
            elts = [e for e in self.elts if e in self.restrain]
        else:
            elts = self.elts.copy()
        return elts

    def scan(self, *args):
        results = super().scan(*args)
        if not isinstance(results, tuple):
            results = tuple([results])
        if len(results) != len(self.elts):
            raise TypeError("Scan function '{}' did not return expected"
                            " number of results. Expected {}, returned {}"
                            .format(self.func.__name__, self.elts, len(results)))
        if self.restrain is not None:
            results = self.restrain_results(results)
        return dict(zip(self.returns, results))

    def copy(self):
        return self.__class__(self.kind, self.func,
                              self.elts.copy(), **self.kwargs.copy())

    def __repr__(self):
        s = ' - '.join([self.kind, self.func.__name__, str(self.elts)])
        if self.restrain is not None:
            s += ' (restrained to {})'.format(self.restrain)
        return s

    def restrain_results(self, results):
        indices = [self.elts.index(r) for r in self.restrain]
        return tuple([results[i] for i in indices])


def make_scanner(kind, elts):
    def decorator(func):
        return ScannerCS(kind, func, elts)
    return decorator


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
        self.scanners = []
        self.manual = set()
        self.elts = ['values', 'in_idx']
        self.fixed_elts = {}

        self.change_units_custom = None

        self.values = []
        self.in_idx = []

        self.force_idx_descending = False

    def __repr__(self):
        s = [super().__repr__()]
        s.append(["In", "Shared"][self.shared])
        s.append("To scan: {}".format(', '.join(self.scanners)))
        if self.scanned:
            s.append("Scanned")
        else:
            s.append("Not scanned")
        if len(self.in_idx) > 0:
            if all([c == self.in_idx[0] for c in self.in_idx]):
                s.append("In-file index is {}".format(str(self.in_idx[0])))
        return '\n'.join(s)

    def reset(self):
        """Remove values."""
        self.empty()
        for elt in self.elts:
            setattr(self, elt, [])

    def update_values(self, values, **elts):
        """Update values.

        Make sure in_idx has same dimensions.
        """
        if not all([len(v) == len(values) for v in elts.values()]):
            raise IndexError("Lenght for '{}' (%d) different have different lengths.")
        for name, elt_val in elts.items():
            if len(values) != len(elt_val):
                raise IndexError("Not as much '{}' ({}) as values ({})"
                                 .format(name, len(elt_val), len(values)))
            setattr(self, name, np.array(elt_val))
        self.values = values
        super().update_values(values)

    def sort_values(self) -> np.ndarray:
        """Sort by values.

        :returns: The order used to sort values.
        """
        order = np.argsort(self.values).tolist()
        for elt in self.elts:
            new_elt = [getattr(self, elt)[i] for i in order]
            setattr(self, elt, new_elt)
        return order

    def slice(self, key: KeyLikeInt):
        k = Key(key)
        for elt in self.elts:
            setattr(self, elt, k.apply(getattr(self, elt)))
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
                indices = key.apply(self.in_idx)

            key_data = key.__class__(indices)
        except Exception:
            log.error("Error in retrieving in-file indices of '%s' for values %s.",
                      self.name, key)
            raise

        return key_data

    def is_to_scan(self) -> bool:
        """If the coord needs any kind of scanning."""
        out = any([s.kind in ['in', 'filename'] for s in self.scanners])
        return out

    def is_to_check(self) -> bool:
        """If the coord values need to be checked."""
        out = self.is_to_scan() or self.manual
        return out

    def remove_scanners(self, kind=None):
        if kind is None:
            kind = ['in', 'filename', 'manual']
        for k in kind:
            self.scanners[k].clear()

    def add_scan_function(self, func: Union[Callable, ScannerCS],
                          elts: List[str] = None, kind=None,
                          restrain: List[str] = None, **kwargs: Any):
        """Set function for scanning values in filename.

        :param elts: Elements to scan ('values', 'in_idx')
        :param kwargs: [opt]

        See also
        --------
        scan_filename_default: for the function signature.
        """
        if isinstance(func, ScannerCS):
            func = func.copy()
            if kind is not None and kind != func.kind:
                raise ValueError("Scanner '{}' kind different from specified."
                                 .format(func.name))
            func.kwargs = kwargs
            if elts is not None:
                if len(func.elts) != len(elts):
                    raise IndexError("Scanner '{}' returns {}, of incompatible"
                                     " lenght with specified {}"
                                     .format(func.name, func.elts, elts))
                func.elts = elts
        else:
            if kind is None or elts is None:
                raise TypeError("Scanner kind and elements must be indicated"
                                " when supplying function '{}'"
                                .format(func.__name__))
            func = ScannerCS(kind, func, elts, **kwargs)
        if restrain is not None:
            out = set(restrain) - set(func.elts)
            if out:
                raise KeyError("Restrain elements {} are not in scanner '{}'"
                               " elements".format(out, func.name))
            func.restrain = restrain
        self.scanners.append(func)

    def set_values_manual(self, **elts):
        """Set values manually."""
        self.manual += elts.keys()
        if 'values' not in elts:
            raise TypeError("Values should be indicated when setting elements")
        self.update_values(elts.pop('values'), **elts)

    def set_values_constant(self, **elts):
        for elt, value in elts.items():
            if elt not in self.elts:
                raise KeyError(f"'{elt}' not in '{self.name}' CoordScan elements.")
            elif elt == 'values':
                raise TypeError("Values cannot set to be constant.")
            self.fixed_elts[elt] = value

    def set_scan_attributes_func(self, func: Callable):
        """Set function for scanning attributes in file.

        See also
        --------
        scan_attributes_default: for the function signature
        """
        self.scanners.append(Scanner('attrs', func))

    def scan_attributes(self, file: File):
        """Scan coordinate attributes if necessary.

        Using the user defined function.
        Apply them.
        """
        for s in self.scanners:
            if s.kind == 'attrs':
                attrs = s.scan(self, file)
                log.debug("Found coordinates attributes %s", list(attrs.keys()))
                for name, value in attrs.items():
                    self.set_attr(name, value)

    def scan_elements(self, file: File):
        elts = {e: [] for e in self.elts}

        for s in self.scanners:
            if s.kind == 'filename':
                log.debug("Scanning filename for '%s'", self.name)
                args = [elts['values']]
            elif s.kind == 'in':
                log.debug("Scanning in file for '%s'", self.name)
                args = [file, elts['values']]

            elts.update(s.scan(self, *args))

        for name, values in elts.items():
            if isinstance(values, np.ndarray):
                elts[name] = values.tolist()
            if not isinstance(values, list):
                elts[name] = [values]
            if name in self.fixed_elts:
                elts[name] = [self.fixed_elts[name]
                              for _ in range(len(elts['values']))]

        if not all([len(values) for values in elts.values()]):
            raise IndexError("Scan results do not all have the same length. "
                             "({})".format({n: len(v) for n, v in elts.items()}))
        return elts

    def append_elements(self, **elts):
        for name, values in elts.items():
            if name == 'values':
                n_values = len(values)
                if n_values == 1:
                    log.debug("Found value %s", values[0])
                else:
                    log.debug("Found %s values between %s and %s",
                              n_values, values[0], values[-1])
            current = getattr(self, name)
            if isinstance(values, list):
                current += values
            else:
                current.append(values)

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
        self.elts.append('dimensions')
        self.dimensions = []


class CoordScanIn(CoordScan):
    """Coord used for scanning of a 'in' coordinate.

    Only scan the first file found.
    All files are thus considered to have the same structure.
    """
    def __init__(self, *args, **kwargs):
        self.scanned = False
        kwargs.pop('shared', None)
        super().__init__(*args, **kwargs, shared=False)

    def scan_file(self, m: re.match, file: File):
        """Scan file.

        :param m: Match of the filename against the regex.
        :param file: Object to access file.
            The file is already opened by FilegroupScan.open_file().
        """
        if not self.scanned and self.is_to_scan():
            elts = self.scan_elements(file)
            self.append_elements(**elts)
            self.scanned = True

    def is_to_open(self) -> bool:
        """If a file is to be open for scanning."""
        out = (not self.scanned
               and any([s.kind in ['in', 'attrs'] for s in self.scanners]))
        return out


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

    def update_values(self, values, matches=None, **elts):
        """Update values.

        Make sure matcher has same dimensions.
        """
        super().update_values(values, **elts)
        if matches is not None:
            if len(values) != len(self.matches):
                raise IndexError("Not as much values as matches.")
            self.matches = matches

    def sort_values(self) -> np.ndarray:
        order = super().sort_values()
        self.matches = [self.matches[i] for i in order]
        return order

    def reset(self):
        super().reset()
        self.matches = []

    def slice(self, key: Union[List[int], slice]):
        k = Key(k)
        self.matches = k.apply(self.matches)
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
        matches = tuple(matches)
        log.debug("Found matches %s for filename %s", matches, m.group())

        # If multiple shared coord, this match could already been found
        if matches not in self.matches:
            elts = self.scan_elements(file)
            self.append_elements(**elts, matches=matches)

    def is_to_open(self) -> bool:
        """If the file must be opened for scanning. """
        out = any([s.kind in ['in', 'attrs'] for s in self.scanners])
        return out


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
