"""Manages scanning of data files."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK

import logging
from typing import (Any, Callable, Dict, Iterable, Iterator, List, Optional,
                    Type, TYPE_CHECKING)

import os
import re

import numpy as np


from tomate.coordinates.coord import Coord
from tomate.custom_types import File, KeyLike
from tomate.filegroup.coord_scan import CoordScan, get_coordscan
from tomate.filegroup.matcher import Matcher
from tomate.filegroup.scanner import Scanner
from tomate.filegroup.spec import CoordScanSpec
from tomate.keys.key import Key, KeyValue
from tomate.variables_info import VariablesInfo
if TYPE_CHECKING:
    from tomate.data_base import DataBase

log = logging.getLogger(__name__)


class FilegroupScan():
    """Manages set of files on disk.

    Files which share the same structure and filenames.
    This class manages the scanning part of filegroups.

    :param root: Root data directory containing all files.
    :param db: Parent database.
    :param coords_fg: Coordinates present in those files, see
        :class:`CoordScanSpec <tomate.filegroup.spec.CoordScanSpec>` for
        details.
    :param vi: Global VariablesInfo instance.
    :param name: [opt] Name of the filegroup.

    :attr root: str: Root data directory containing all files.
    :attr db: DataBase: Parent database.
    :attr vi: VariablesInfo: Global VariablesInfo instance.
    :attr name: str: Name of the filegroup.

    :attr pregex: str: Pre-regex.
    :attr regex: str: Regex.
    :attr file_override: str: If filegroup consist of a single file, this is
        used (instead of a regular expression). DEPRECATED in v2.3.0, use
        Constructor.set_file_override instead.
    :attr files: str: List of files that will be scanned.

    :attr found_file: bool: If any file matching the regex has been found.
    :attr n_matcher: int: Number of matchers in the pre-regex.
    :attr segments: List[str]: Fragments of filename used for reconstruction,
        elements with pair indices are replaced with matches.

    :attr cs: Dict[str, CoordScan]: Dictionnary of scanning coordinates, each
        dynamically inheriting from its parent Coord.
    :attr selection: Dict[str, Union[KeyLike, KeyLikeValue]]:
        Keys for selecting parts of each CoordScan, by index or value.
    :attr post_loading_funcs: List[Tuple[Callable, Key, bool, Dict]]:
        Functions applied after loading data.
        Each element is a tuple of the function, the variable that triggers
        the call, a boolean True if all said variables must present to trigger,
        False if any variable must be loaded, and kwargs to pass.
    """

    MAX_DEPTH_SCAN = 3
    """Limit descending into lower directories when finding files."""

    def __init__(self, root: str,
                 db: 'DataBase',
                 coords_fg: List[CoordScanSpec],
                 vi: VariablesInfo,
                 name: str = ''):
        self.root = root
        self.db = db
        self.vi = vi
        self.name = name

        self.regex = ""
        self.pregex = ""
        self.files = []

        self.found_file = False
        self.n_matcher = 0
        self.segments = []

        self.scanners = []

        self.cs = {}
        self.make_coord_scan(coords_fg)

        self.post_loading_funcs = []
        self.selection = {}

    @property
    def variables(self) -> List[str]:
        """List of variables contained in this filegroup."""
        cs = self.cs['var']
        if cs.has_data():
            return cs[:].tolist()
        return []

    @property
    def contains(self) -> Dict[str, Optional[np.ndarray]]:
        """Index of values contained in this filegroup.

        Indexed on available scope. None designate a value not contained.
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

    def __setattr__(self, name, value):
        if name == 'file_override':
            log.warning("file_override will be deprecated in 2.3.0, "
                        "use Constructor.set_file_override instead")
            super().__setattr__('files', [value])
        super().__setattr__(name, value)

    def add_variable(self, name: str, infile: KeyLike = '__equal_to_name__',
                     dimensions: List[str] = None):
        """Add variable to filegroup.

        :param name: Name of the variable.
        :param infile: Infile key of the variable. If None,
        :param dimensions: Infile dimensions of the variable. If None,
            all dimensions from variable are used.
        """
        if infile == '__equal_to_name__':
            infile = name
        if dimensions is None:
            dimensions = self.db[name].dims
        self.cs['var'].append_elements(values=name, in_idx=infile,
                                       dimensions=tuple(dimensions))
        self.cs['var'].self_update()

    def make_coord_scan(self, coords: CoordScanSpec):
        """Add CoordScan objects.

        Each CoordScan is dynamically rebased from its parent Coord.
        """
        self.cs = {}
        for c in coords:
            cs = get_coordscan(self, c.coord, c.shared, c.name)
            self.cs.update({c.coord.name: cs})

    def iter_shared(self, shared: bool = None) -> Dict[str, CoordScan]:
        """Iter through CoordScan objects.

        :param shared: [opt] To iterate only shared coordinates (shared=True),
            or only in coordinates (shared=False). If left to None, iter all
            coordinates.
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

        Create a proper regex from the pre-regex. Find the matchers, replace
        them by the appropriate regex, store segments for easy replacement by
        the matches later.

        :param pregex: Pre-regex.
        :param replacements: Matchers to be replaced by a constant.
            The arguments names must match a matcher in the pre-regex.

        :raises KeyError: A matcher has an unknown dimension.
        :raises TypeError: A dimensions is not shared but has a matcher.
        :raises IndexError: A dimension is shared but has not matcher.

        Example
        -------
        >>> pregex = "%(prefix)_%(time:value)"
        ... replacements = {"prefix": "SST"}
        """
        pregex = pregex.strip()

        for k, z in replacements.items():
            pregex = pregex.replace("%({:s})".format(k), z)

        m = self.scan_pregex(pregex)

        idx = -1  # If no matcher, we get n_matcher = 0, see below
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
        """Scan pregex for matchers. """
        regex = r"%\(([a-zA-Z]*):([a-zA-Z]*)(?P<cus>:custom=)?((?(cus)[^:]+:))(:?dummy)?\)"
        m = re.finditer(regex, pregex)
        return m

    def find_segments(self, m: Iterator[re.match]):
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

        Tomate does exception handling with the `with` statement.
        The returned object should support it.

        :param filename: File to open.
        :param mode: Mode for opening (read only, replace, append, ...)
        :param log_lvl: {'debug', 'info', 'warning'} Level to log the opening at.
        """
        raise NotImplementedError

    def is_to_open(self) -> bool:
        """Return if the current file has to be opened."""
        to_open = (any(cs.is_to_open() for cs in self.cs.values())
                   or any(s.kind == 'gen' for s in self.scanners))
        return to_open

    def scan_coordinates_objects(self, func: Callable, **kwargs: Any) -> List[Coord]:
        """Scan coordinates objects.

        If files were not already found, launch `find_files`.

        Add found dimensions to `cs`.
        """
        if not self.files:
            self.find_files()

        if len(self.files) == 1:
            filename = self.files[0]
        else:
            filename = ''
            # We could remove non-matches from files, or they will be rematched
            # later. Not a big deal.
            for f in self.files:
                m = re.match(self.regex, f)
                if m is not None:
                    filename = f
                    break
            if not filename:
                raise NameError("No files matching the regex.")

        with self.open_file(os.path.join(self.root, filename),
                            log_lvl='DEBUG') as file:
            coords = func(file, **kwargs)
            coords_return = []  # Only return coords not already in FG
            for c in coords:
                log.debug("Found dimensions '%s' of class %s",
                          c.name, c.__class__.__name__)
                if c.name not in [c.name for c in self.cs.values()]:
                    coords_return.append(c)
                    cs = get_coordscan(self, c, False, c.name)
                    self.cs[c.name] = cs

        return coords_return

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

        Match filename against regex. If first match, retrieve segments.

        If needed, open file. Scan general attributes. For all CoordScan, scan
        coordinate attributes, scan elements.

        Close file.
        """
        def execute_scanning(file):
            self.scan_general_attributes(file)

            for cs in self.cs.values():
                cs.scan_attributes(file)
                cs.scan_file(m, file)

        m = re.match(self.regex, filename)

        # Discard completely non matching files
        if m is None:
            return

        if not self.found_file:
            self.find_segments(m)

        self.found_file = True

        if self.is_to_open():
            with self.open_file(os.path.join(self.root, filename),
                                mode='r', log_lvl='debug') as file:
                execute_scanning(file)
        else:
            execute_scanning(None)

    def find_files(self):
        """Find files to scan.

        Uses os.walk. Limit search to `MAX_DEPTH_SCAN` levels of directories
        deep.

        If `file_override` is set, bypass this search, just use it.

        Sort files alphabetically.

        :raises AttributeError: If no regex is set.
        :raises IndexError: If no files are found.
        """
        if self.regex == '':
            raise AttributeError(f"Filegroup '{self.name}' is missing a regex.")

        files = []
        for root, _, files_ in os.walk(self.root):
            depth = len(os.path.relpath(root, self.root).split(os.sep)) - 1
            if depth > self.MAX_DEPTH_SCAN:
                break
            files += [os.path.relpath(os.path.join(root, file), self.root)
                      for file in files_]
        files.sort()

        if len(files) == 0:
            raise IndexError(f"No files were found in {self.root}")

        log.debug("Found %s files in %s", len(files), self.root)

        self.files = files

    def scan_files(self):
        """Scan files.

        Reset scanning coordinate if they are to scan. Find files. Scan each
        file. Set CoordScan elements.

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

        if not self.files:
            self.find_files()
        for file in self.files:
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
                    log.warning("Units conversion should happen for '%s' (%s) "
                                "from '%s' to '%s' but no function is defined.",
                                cs.name, self.name, cs.units, cs.coord.units)

            if len(cs.values) == 0:
                raise ValueError("No values detected ({0}, {1})".format(
                    cs.name, self.name))
            cs.update_values(cs.values)

    def add_scan_attrs_func(self, func: Callable,
                            kind: str = None, **kwargs: Any):
        """Add a function for scanning attributes."""
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


def make_filegroup(fg_type: Type, root: str, dims: Dict[str, Coord],
                   coords_fg: Iterable[CoordScanSpec],
                   vi: VariablesInfo,
                   root_fg: str = None, name: str = '',
                   variables_shared: bool = False,
                   **kwargs: Any):
    """Convenience function to create filegroup.

    :param fg_type: Class of filegroup to add. Dependant on the file-format.
    :param root: Database root directory.
    :param dims: List of parent coordinates.
    :param coords_fg: Coordinates used in this grouping of files. Each
        element is an :class:`CoordScanSpec
        <tomate.filegroup.spec.CoordScanSpec>`. See its documentation
        for details.
    :param vi: Global VariablesInfo instance.
    :param root_fg: Subfolder, relative to root.
    :param name: Name of the filegroup.
    :param variables_shared: [opt] If the Variables dimension is shared.
        Default is False.
    :param kwargs: [opt] Passed to the `fg_type` initializator.
    """
    for css in coords_fg:
        css.process(dims)

    if root_fg is None:
        root_fg = ''
    root_fg = os.path.join(root, root_fg)

    coords_fg = list(coords_fg)
    if all(css.coord.name != 'var' for css in coords_fg):
        coords_fg.insert(0, CoordScanSpec(dims['var'], variables_shared, 'var'))
    fg = fg_type(root_fg, None, coords_fg, vi, name, **kwargs)

    return fg


def scan_coordinates_objects_default(file: File, **kwargs: Any):
    """Retrieve coordinates object from a file.

    :param file: Object to acees file. The file is already opened by
        FilegroupScan.open_file().

    :return: List of subclass of Coord instances. Only coordinates not already
        present in the filegroup will be kept.
    """
    raise NotImplementedError()
