"""Manages scanning of data files."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import logging
from typing import (Any, Callable, Dict, Iterable, Iterator, List, Optional,
                    Type, TYPE_CHECKING, Union)

import os
import re

import numpy as np


from tomate.coordinates.coord import Coord
from tomate.custom_types import File
from tomate.filegroup.coord_scan import CoordScan, get_coordscan
from tomate.filegroup.matcher import Matcher
from tomate.filegroup.scanner import Scanner
from tomate.filegroup.spec import CoordScanSpec
from tomate.keys.key import Key, KeyValue
from tomate.variables_info import VariablesInfo
if TYPE_CHECKING:
    from tomate.filegroup.filegroup_load import FilegroupLoad
    from tomate.data_base import DataBase

log = logging.getLogger(__name__)


class FilegroupScan():
    """Manages set of files on disk.

    Files which share the same structure and filenames.
    This class manages the scanning part of filegroups.

    :param root: Root data directory containing all files.
    :param db: Parent database.
    :param coords_fg: Parent coordinates objects,
        a bool indicating if the coordinate is shared accross files,
        and their name inside files.
    :param vi: Global VariablesInfo instance.
    :param name: [opt] Name of the filegroup.

    :attr root: str: Root data directory containing all files.
    :attr db: DataBase: Parent database.
    :attr vi: VariablesInfo: Global VariablesInfo instance.
    :attr name: str: Name of the filegroup.

    :attr cs: Dict[str, CoordScan or subclass]: Dictionnary of scanning
        coordinates, each dynamically inheriting from its parent Coord.

    :attr pregex: str: Pre-regex.
    :attr regex: str: Regex.
    :attr file_override: str: If filegroup consist of a single file,
        this is used (instead of a regular expression)

    :attr segments: List[str]: Fragments of filename used for reconstruction,
        elements with pair indices are replaced with matches.

    :attr scan_attr: Dict[str, [Callable, scanned:bool, kwargs: Dict]]:
        Functions to call to scan variables specific
        attributes or general attributes.
        Key is 'gen' for general attributes, 'var' for variable specific.
        Value is a tuple of the function to call, a boolean if the attributes
        have been scanned, and kwargs to pass to the function.

    :attr selection: Dict[str, Union[KeyLike, KeyLikeValue]]:
        Keys for selecting parts of the CoordScan, by index or value.
        Dict key is dimension name.

    :attr post_loading_funcs: List[Tuple[Callable, Key, bool, Dict]]:
        Functions applied after loading data.
        Each element is a tuple of the function, the variable that triggers
        the call, a boolean True if all said variables must present to trigger,
        False if any variable must be loaded, and kwargs to pass.
    """

    MAX_DEPTH_SCAN = 3

    def __init__(self, root: str,
                 db: 'DataBase',
                 coords_fg: List[CoordScanSpec],
                 vi: VariablesInfo,
                 name: str = ''):
        self.root = root
        self.db = db
        self.vi = vi
        self.name = name

        self.found_file = False
        self.n_matcher = 0
        self.segments = []

        self.regex = ""
        self.pregex = ""
        self.file_override = ''

        self.scanners = []

        self.cs = {}
        self.make_coord_scan(coords_fg)

        self.post_loading_funcs = []
        self.selection = {}

    @property
    def variables(self) -> List[str]:
        """List of variables contained in this filegroup."""
        return self.cs['var'].to_list()

    @property
    def contains(self) -> Dict[str, Optional[np.ndarray]]:
        """Index of values contained in this filegroup.

        Indexed on available scope.
        None designate a value not contained.
        """
        out = {name: c.contains for name, c in self.cs.items()}
        return out

    def __repr__(self):
        s = [str(self),
             f"Root directory: {self.root}",
             f"Pre-regex: {self.pregex}",
             f"Regex: {self.regex}",
             ""]

        s.append("Coordinates for scan:")
        for name, cs in self.cs.items():
            s1 = ['{} ({})'.format(name, cs.name)]
            s1.append(', {}'.format(['in', 'shared'][cs.shared]))
            if cs.has_data():
                s1.append(': {}, {}'.format(cs.get_extent_str(), cs.size))
            s.append(''.join(s1))
        return '\n'.join(s)

    def __str__(self):
        return "{}: {}".format(self.__class__.__name__, self.name)

    def make_coord_scan(self, coords: CoordScanSpec):
        """Add CoordScan objects.

        Each CoordScan is dynamically rebased
        from its parent Coord.

        :param coords: List of tuple containing the coordinate object,
            the shared flag, and the name of the coordinate infile.
        """
        self.cs = {}
        for c in coords:
            cs = get_coordscan(self, c.coord, c.shared, c.name)
            self.cs.update({c.coord.name: cs})

    def iter_shared(self, shared: bool = None) -> Dict[str, CoordScan]:
        """Iter through CoordScan objects.

        :param shared: [opt] To iterate only shared coordinates (shared=True),
            or only in coordinates (shared=False).
            If left to None, iter all coordinates.
        """
        cs = {}
        for name, c in self.cs.items():
            add = False
            if shared is None:
                add = True
            else:
                add = (c.shared == shared)

            if add:
                cs[name] = c

        return cs

    def set_scan_regex(self, pregex: str, **replacements: str):
        """Specify the pre-regex.

        Create a proper regex from the pre-regex.
        Find the matchers: replace them by the appropriate regex,
        store segments for easy replacement by the matches later.

        :param pregex: Pre-regex.
        :param replacements: Matchers to be replaced by a constant.
            The arguments names must match a matcher in the pre-regex.

        Example
        -------
        >>> pregex = "%(prefix)_%(time:value)"
        ... replacements = {"prefix": "SST"}
        """
        pregex = pregex.strip()

        for k, z in replacements.items():
            pregex = pregex.replace("%({:s})".format(k), z)

        m = self.scan_pregex(pregex)

        # Separations between segments
        idx = -1
        regex = pregex
        for idx, match in enumerate(m):
            matcher = Matcher(match, idx)
            if matcher.coord not in self.cs:
                raise KeyError("{} has no scanning coordinate '{}'."
                               .format(self.name, matcher.coord))
            if not self.cs[matcher.coord].shared:
                raise TypeError(f"'{matcher.coord}' is not shared but has a matcher.")
            self.cs[matcher.coord].add_matcher(matcher)
            regex = regex.replace(match.group(), '(' + matcher.rgx + ')')

        for name, cs in self.iter_shared(True).items():
            if len(cs.matchers) == 0:
                raise IndexError(f"'{name}' in filegroup '{self.name}' is "
                                 "shared but has no matcher in the pre-regex.")

        self.n_matcher = idx + 1
        self.regex = regex
        self.pregex = pregex

    @staticmethod
    def scan_pregex(pregex: str) -> Optional[Iterator[re.match]]:
        """Scan pregex for matchers.

        :param pregex: Pre-regex.
        """
        regex = r"%\(([a-zA-Z]*):([a-zA-Z]*)(?P<cus>:custom=)?((?(cus)[^:]+:))(:?dummy)?\)"
        m = re.finditer(regex, pregex)
        return m

    def find_segments(self, m: Optional[Iterator[re.match]]):
        """Find segments in filename.

        Store result.

        :param m: Matches of the pre-regex to find matchers.
        """
        sep = [0]
        n = len(m.groups())
        for i in range(n):
            sep.append(m.start(i+1))
            sep.append(m.end(i+1))

        s = m.string
        self.segments = [s[i:j]
                         for i, j in zip(sep, sep[1:]+[None])]

    def open_file(self, filename: str,
                  mode: str = 'r',
                  log_lvl: str = 'info',
                  **kwargs: Any) -> File:
        """Open a file.

        :param filename: File to open.
        :param mode: Mode for opening (read only, replace, append, ...)
        :param log_lvl: {'debug', 'info', 'warning'} Level to log the opening at.
        """
        raise NotImplementedError

    def close_file(self, file: File):
        """Close file."""
        raise NotImplementedError

    def is_to_open(self) -> bool:
        """Return if the current file has to be opened."""
        to_open = (any(cs.is_to_open() for cs in self.cs.values())
                   or any(s.kind == 'gen' for s in self.scanners))
        return to_open

    def scan_general_attributes(self, file: File):
        """Scan for general attributes."""
        for s in self.scanners:
            if s.kind == 'gen' and s.to_scan:
                log.debug('Scanning file for general attributes.')
                infos = s.scan(self, file)
                log.debug("Found infos %s", list(infos.keys()))
                self.vi.set_infos_default(**infos)

    def scan_file(self, filename: str):
        """Scan a single file.

        Match filename against regex.
        If first match, retrieve segments.

        If needed, open file.
        Scan general attributes.
        For all CoordScan, scan coordinate attributes,
        scan values, and in-file indices.

        Close file.
        """
        m = re.match(self.regex, filename)
        filename = os.path.join(self.root, filename)

        # Discard completely non matching files
        if m is None:
            return

        if not self.found_file:
            self.find_segments(m)

        self.found_file = True

        file = None
        if self.is_to_open():
            file = self.open_file(filename, mode='r', log_lvl='debug')

        try:
            self.scan_general_attributes(file)

            for cs in self.cs.values():
                cs.scan_attributes(file)
                cs.scan_file(m, file)
        except Exception:
            if file is not None:
                self.close_file(file)
            log.error("Error in scanning filegroup %s", self.name)
            raise
        else:
            if file is not None:
                self.close_file(file)

    def find_files(self) -> List[str]:
        """Find files to scan.

        Uses os.walk. Sort files alphabetically

        :raises IndexError: If no files are found.
        """
        if self.file_override:
            return [self.file_override]

        files = []
        for i, (root, _, files_) in enumerate(os.walk(self.root)):
            if i > self.MAX_DEPTH_SCAN:
                break
            files += [os.path.relpath(os.path.join(root, file), self.root)
                      for file in files_]
        files.sort()

        if len(files) == 0:
            raise IndexError(f"No files were found in {self.root}")

        log.debug("Found %s files in %s", len(files), self.root)

        return files

    def scan_files(self):
        """Scan files.

        Reset scanning coordinate if they are to scan.
        Find files.
        Scan each file.
        Set CoordScan values.

        :raises NameError: If no files matching the regex were found.
        :raises ValueError: If no values were detected for a coordinate.
        """
        for s in self.scanners:
            s.to_scan = True
        # Reset CoordScan
        for cs in self.cs.values():
            cs.scanned = False
            for s in cs.scanners:
                s.to_scan = True
            if not cs.manual:
                cs.reset()
        self.found_file = False

        files = self.find_files()
        for file in files:
            self.scan_file(file)

        if not self.found_file:
            raise NameError("No file matching the regex found ({}, regex={})"
                            .format(self.name, self.regex))

        for cs in self.cs.values():
            for elt, value in cs.fixed_elts.items():
                cs.update_values(cs.values,
                                 **{elt: [value for _ in range(len(cs.values))]})

            cs.sort_elements()

            if (cs.coord.name != 'var'
                    and cs.units != '' and cs.coord.units != ''
                    and cs.units != cs.coord.units):
                if cs.change_units_custom is not None:
                    f = cs.change_units_custom
                else:
                    f = cs.change_units_other
                log.debug("Changing units for '%s' from '%s' to '%s'",
                          cs.coord.name, cs.units, cs.coord.units)
                try:
                    cs.values = f(cs.values, cs.units, cs.coord.units)
                except NotImplementedError:
                    log.warning("Units conversion should happen for '%s' (%s)"
                                " from '%s' to '%s' but no function is defined.",
                                cs.name, self.name, cs.units, cs.coord.units)

            if len(cs.values) == 0:
                raise ValueError("No values detected ({0}, {1})".format(
                    cs.name, self.name))
            cs.update_values(cs.values)

    def add_scan_attrs_func(self, func: Callable,
                            kind: str = None, **kwargs: Any):
        """Add the function for scanning attributes."""
        func = Scanner(kind, func, **kwargs)
        if func.kind not in ['var', 'gen']:
            raise KeyError("Attributes scanner kind should be 'gen' or 'var'")
        self.scanners.append(func)

    def apply_coord_selection(self):
        """Apply CoordScan selection."""
        for dim, key in self.selection.items():
            cs = self.cs[dim]
            if isinstance(key, KeyValue):
                key = Key(key.apply(cs))
            log.debug("Slicing '%s' in filegroup '%s' with indices %s",
                      dim, self.name, key.no_int())
            cs.slice(key.no_int())


def make_filegroup(fg_type: Type, root: str, dims: List[Coord],
                   coords_fg: Iterable[CoordScanSpec],
                   vi: VariablesInfo,
                   root_fg: str = None, name: str = '',
                   variables_shared: bool = False,
                   **kwargs: Any):
    """Convenience function to create filegroup.

    :param fg_type: Class of filegroup to add. Dependant on the file-format.
    :param root: Base root.
    :param coords_fg: Coordinates used in this grouping of files.
        Each element of the list is a tuple of length 2 or 3 with
        the coordinate (or its name), a shared flag, and eventually
        the name of the coordinate in the file.
        The flag can be 'shared' or 'in', or a boolean (True = shared).
        The name is optional, if not specified the name of the coordinate
        object is used.
        Variables dimension can be omitted.
    :param name: Name of the filegroup.
    :param root_fg: [opt] Subfolder from root.
    :param variables_shared: [opt] If the Variables dimension is shared.
        Default is False.
    :param kwargs: [opt] Passed to the fg_type initializator.
    """
    for css in coords_fg:
        css.process(dims)

    if root_fg is None:
        root_fg = ''
    root_fg = os.path.join(root, root_fg)

    if all(css.coord.name != 'var' for css in coords_fg):
        coords_fg.insert(0, CoordScanSpec(dims['var'], variables_shared, 'var'))
    fg = fg_type(root_fg, None, coords_fg, vi, name, **kwargs)

    return fg
