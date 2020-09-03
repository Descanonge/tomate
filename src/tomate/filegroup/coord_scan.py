"""This is where the scanning is happening.

Handles scanning of elements in filenames and files.

See :doc:`../scanning` and :doc:`../coord`.
"""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Sequence, Union
import re

import numpy as np

from tomate.coordinates.coord import Coord
from tomate.custom_types import File, KeyLike
from tomate.filegroup.matcher import Matcher
from tomate.filegroup.scanner import Scanner, ScannerCS
from tomate.keys.key import Key, list2slice

if TYPE_CHECKING:
    from tomate.filegroup.filegroup_load import FilegroupLoad


log = logging.getLogger(__name__)


class CoordScan(Coord):
    """Coord used for scanning of one dimension.

    Abstract class meant to be subclassed into CoordScanIn or CoordScanShared.

    :param filegroup: Corresponding filegroup.
    :param coord: Parent coordinate.
    :param shared: If the coordinate is shared accross files.
    :param name: Name of the coordinate in file.

    :attr filegroup: FilegroupLoad: Corresponding filegroup.
    :attr coord: Coord: Parent coordinate object.
    :attr contains: Optional[np.ndarray]: For each value of the available scope,
        the index of the corresponding value in that CS. If that value is not
        contained in this filegroup, the index is None.
    :attr shared: bool: If the coordinate is shared accross files.

    :attr elts: List[str]: Elements to be scanned.
    :attr values: List: Values found for this coordinate.
    :attr in_idx: List: Index for each value inside the files.

    :attr scanners: List[ScannerCS]: List of scanners to use to scan coordinates
        elements.
    :attr scanners_attrs: List[Scanner]: List of scanners to use to scan
        attributes.
    :attr manual: Set[str]: Elements that are set manually.
    :attr fixed_elts: Dict[str, Any]: Elements fixed to a constant.

    :attr change_units_custom: Callable: Function that will override
        `change_units_other`.
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
        self.elts = ['values', 'in_idx']
        self.values = []
        self.in_idx = []

        self.scanners = []
        self.scanners_attrs = []
        self.manual = set()
        self.fixed_elts = {}

        self.change_units_custom = None

    def __repr__(self):
        s = [super().__repr__()]
        s.append("Kind: {}".format(["In", "Shared"][self.shared]))

        if len(self.in_idx) > 0:
            if all(c == self.in_idx[0] for c in self.in_idx):
                s.append("In-file index is {}".format(str(self.in_idx[0])))

        if self.scanners:
            s.append("To scan:")
            s += ['\t' + str(s) for s in self.scanners]
        if self.fixed_elts:
            s.append("Fixed elements: ")
            s += ["\t{} = {}".format(e, v) for e, v in self.fixed_elts.items()]

        return '\n'.join(s)

    def __str__(self):
        s = "{} ({}): {}".format(self.__class__.__name__,
                                 self.coord.__class__.__name__, self.name)
        return s

    def reset(self):
        """Remove elements."""
        self.empty()
        for elt in self.elts:
            if elt not in self.fixed_elts:
                setattr(self, elt, [])

    def self_update(self):
        """Update values and elements from its attributes."""
        elts = {elt: getattr(self, elt) for elt in self.elts}
        self.update_values(**elts)

    def update_values(self, values: Sequence, **elts: Sequence):
        """Update values and elements.

        :raises IndexError: If an element does not have same length as values.
        """
        for name, elt_val in elts.items():
            if len(values) != len(elt_val):
                raise IndexError("Not as much '{}' ({}) as values ({})"
                                 .format(name, len(elt_val), len(values)))
            setattr(self, name, elt_val)
        self.values = values
        super().update_values(values)

    def sort_elements(self) -> np.ndarray:
        """Sort by values.

        :returns: The order used to sort values.
        """
        order = np.argsort(self.values).tolist()
        for elt in self.elts:
            new_elt = [getattr(self, elt)[i] for i in order]
            setattr(self, elt, new_elt)
        return order

    def slice(self, key: KeyLike):
        k = Key(key)
        for elt in self.elts:
            setattr(self, elt, k.apply(getattr(self, elt)))
        if self.size is not None:
            super().slice(key)

    def slice_from_avail(self, key: KeyLike) -> bool:
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

    def is_to_scan(self) -> bool:
        """If the coord has to scan elements."""
        return len(self.scanners) > 0

    def remove_scanners(self, kind=None):
        """Remove scanners.

        :param kind: If None, all kinds are removed.
        """
        if kind is None:
            kind = ['in', 'filename']
        if not isinstance(kind, list):
            kind = [kind]
        self.scanners = [s for s in self.scanners
                         if s.kind not in kind]

    def add_scan_function(self, func: Union[Callable, ScannerCS],
                          elts: List[str] = None, kind: str = None,
                          restrain: List[str] = None, **kwargs: Any):
        """Set function for scanning values in filename.

        :param func: Scanner or callable.
        :param kind: Kind of scanner ('filename' or 'in').
        :param elts: Elements to scan. If `func` is a Scanner, redefine its
            elements.
        :param restrain: Restrain elements to use. Others are ignored.
            If None, use all elements.
        :param kwargs: [opt] Passed to scanning function.
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
                                     " length with specified {}"
                                     .format(func.name, func.elts, elts))
                func.elts = elts
        else:
            if kind is None or elts is None:
                raise TypeError("Scanner kind and elements must be indicated"
                                " when supplying function '{}'"
                                .format(func.__name__))
            func = ScannerCS(kind, func, elts, **kwargs)

        if restrain is None:
            restrain = []
        out = set(restrain) - set(func.elts)
        if out:
            raise KeyError("Restrain elements {} are not in scanner '{}'"
                           " elements".format(out, func.name))
        func.restrain = restrain

        self.scanners.append(func)
        for elt in func.returns:
            self.fixed_elts.pop(elt, None)
        self.manual = set()

    def set_elements_manual(self, **elts: Sequence):
        """Set elements manually.

        Remove all scanners. Remove overlapping fixed elements.
        Wrapper around `update_values`.
        """
        self.manual |= elts.keys()
        self.scanners = []
        for elt in elts:
            self.fixed_elts.pop(elt, None)
        if 'values' not in elts:
            raise TypeError("Values should be indicated when setting elements")
        self.update_values(elts.pop('values'), **elts)

    def set_elements_constant(self, **elts: Any):
        """Set elements as constant.

        They stay the same for all coordinate values. Remove overlapping
        elements set manually. If values were set manually before hand, use
        their length to complete constant elements.
        """
        for elt, value in elts.items():
            if elt not in self.elts:
                raise KeyError(f"'{elt}' not in '{self.name}' CoordScan elements.")
            if elt == 'values':
                raise TypeError("Values cannot be set to a constant.")
            self.fixed_elts[elt] = value
            self.manual -= {elt}
            setattr(self, elt, [value for _ in range(len(self.values))])

    def add_scan_attributes_func(self, func: Callable):
        """Add function for scanning attributes in file.

        See also
        --------
        scan_attributes_default: for the function signature
        """
        self.scanners_attrs.append(Scanner('attrs', func))

    def scan_attributes(self, file: File):
        """Scan coordinate attributes if necessary.

        Using the user defined function. Apply them using `set_attr`.
        """
        for s in self.scanners_attrs:
            attrs = s.scan(self, file)
            log.debug("Found coordinates attributes %s", list(attrs.keys()))
            for name, value in attrs.items():
                self.set_attr(name, value)

    def scan_elements(self, file: File) -> Dict[str, List]:
        """Scan elements.

        :raises IndexError: Elements do not have the same length.
        :returns: Dictionnary of sequences.
        """
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
        for name in self.fixed_elts:
            elts.pop(name, None)

        if not all(len(values) == len(elts['values'])
                   for values in elts.values()):
            raise IndexError("Scan results do not all have the same length. "
                             "({})".format({n: len(v) for n, v in elts.items()}))
        return elts

    def append_elements(self, **elts: Dict[str, Any]):
        """Append elements to those already scanned.

        If an element is a list, it is concatenated to already scanned elements,
        any other type is appended to it.
        """
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
        """Find indices of values present in `outer`.

        :param outer: List of available values.
        :returns:  List of the index of the outer values in the CS.
            If the value is not contained in CS, the index is `None`.
        """
        if self.size is None:
            contains = np.arange(len(outer))
        else:
            contains = []
            for value in outer:
                contains.append(self.get_index_exact(value))
            contains = np.array(contains)

            # Check
            indices = [i for i in contains if i is not None]
            if len(indices) > 2 and isinstance(list2slice(indices), list):
                log.warning("'%s' from '%s' contains discontinuous values "
                            "from all available. This might indicate "
                            "incompatible values accross filegroups, or a "
                            "too small `float_comparison` threshold.",
                            self.name, self.filegroup.name)

        self.contains = contains


class CoordScanIn(CoordScan):
    """Coord used for scanning of a 'in' coordinate.

    Only scan the first file found. All files are considered to have the same
    structure.

    :attr scanned: bool: If coordinate has scanned a file.
    """
    def __init__(self, *args, **kwargs):
        self.scanned = False
        kwargs.pop('shared', None)
        super().__init__(*args, **kwargs, shared=False)

    def scan_file(self, m: re.match, file: File):
        """Scan file.

        :param m: Match of the filename against the regex.
        :param file: Object to access file.
        """
        if not self.scanned and self.is_to_scan():
            elts = self.scan_elements(file)
            self.append_elements(**elts)
            self.scanned = True

    def is_to_open(self) -> bool:
        """If a file is to be open for scanning."""
        out = (not self.scanned
               and (any(s.kind == 'in' for s in self.scanners)
                    or self.scanners_attrs))
        return out


class CoordScanShared(CoordScan):
    """Coord used for scanning of a 'shared' coordinate.

    Coordinate values are shared across multiple files. Scan all files.

    :attr matchers: List[Matcher]: Matcher objects for this coordinate.
    :attr matches: List[List[str]]: List of matches in the filename, for each
        value.
    """

    def __init__(self, *args, **kwargs):
        kwargs.pop('shared', None)
        super().__init__(*args, **kwargs, shared=True)

        self.matchers = []
        self.matches = []

    def __repr__(self):
        s = [super().__repr__()]
        s.append('Matchers:')
        s += ['\t' + str(m) for m in self.matchers]
        return '\n'.join(s)

    @property
    def n_matchers(self) -> int:
        """Numbers of matchers for that coordinate."""
        return len(self.matchers)

    def add_matcher(self, matcher: Matcher):
        """Add a matcher."""
        self.matchers.append(matcher)

    def update_values(self, values: Sequence, matches: Sequence = None,
                      **elts: Sequence):
        """Update values and elements.

        Make sure matcher has same dimensions.
        """
        super().update_values(values, **elts)
        if matches is not None:
            if len(values) != len(self.matches):
                raise IndexError("Not as much values as matches.")
            self.matches = matches

    def sort_elements(self) -> np.ndarray:
        order = super().sort_elements()
        self.matches = [self.matches[i] for i in order]
        return order

    def reset(self):
        super().reset()
        self.matches = []

    def slice(self, key: Union[List[int], slice]):
        k = Key(key)
        self.matches = k.apply(self.matches)
        super().slice(key)

    def scan_file(self, m: re.match, file: File):
        """Scan file.

        :param m: Match of the filename against the regex.
        :param file: Object to access file.
        """
        # Find matches
        matches = []
        for mchr in self.matchers:
            mchr.match = m.group(mchr.idx + 1)
            matches.append(mchr.match)
        log.debug("Found matches %s for filename %s", matches, m.group())

        # If multiple shared coord, this match could already been found
        if matches not in self.matches:
            elts = self.scan_elements(file)
            matches = [matches for _ in range(len(elts['values']))]
            self.append_elements(**elts, matches=matches)

    def is_to_open(self) -> bool:
        """If the file must be opened for scanning. """
        out = (any(s.kind == 'in' for s in self.scanners)
               or self.scanners_attrs)
        return out


def get_coordscan(filegroup: 'FilegroupLoad', coord: Coord,
                  shared: bool, name: str):
    """Get the right CoordScan object derived from a Coord.

    Dynamically create a subclass of CoordScanShared or CoordScanIn, that
    inherits methods from a subclass of Coord.

    :param coord: Coordinate to create a CoordScan object from.
    :param shared: If the coordinate is shared.
    :param name: Name of the coordinate in file.
    """
    coord_type = type(coord)
    CoordScanRB = type("CoordScanRB", (CoordScan, coord_type), {})
    if shared:
        CoordScanType = type("CoordScanSharedRB",
                             (CoordScanShared, CoordScanRB), {})
    else:
        CoordScanType = type("CoordScanInRB",
                             (CoordScanIn, CoordScanRB), {})

    cs = CoordScanType(filegroup, coord, name=name)
    if coord.name == 'var':
        cs.elts.append('dimensions')
    cs.reset()

    return cs


def mirror_key(key: Key, size: int) -> KeyLike:
    """Mirror indices in a key."""
    if key.type == 'int':
        value = size - key.value - 1
    elif key.type in ['list', 'slice']:
        key.parent_size = size
        value = [size - z - 1 for z in key.as_list()]
    return value
