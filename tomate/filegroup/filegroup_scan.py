"""Manages scanning of data files."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import logging
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, TYPE_CHECKING

import os
import re

import numpy as np

import tomate.filegroup.coord_scan as dlcs

from tomate.coordinates.coord import Coord
from tomate.custom_types import File
from tomate.filegroup.coord_scan import CoordScan
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

    :attr post_loading_funcs: List[Tuple[Callable, KeyVar, bool, Dict]]:
        Functions applied after loading data.
        Each element is a tuple of the function, the variable that triggers
        the call, a boolean True if all said variables must present to trigger,
        False if any variable must be loaded, and kwargs to pass.
    """

    def __init__(self, root: str,
                 db: 'DataBase',
                 coords_fg: List[Tuple[Coord, bool, str]],
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

        self.scan_attr = {}

        self.cs = {}
        self.make_coord_scan(coords_fg)

        self.post_loading_funcs = []
        self.selection = {}

    @property
    def variables(self) -> List[str]:
        """List of variables contained in this filegroup."""
        csv = self.cs['var']
        if csv.has_data():
            v = csv[:].tolist()
        else:
            v = []
        return v

    @property
    def contains(self) -> Dict[str, Optional[np.ndarray]]:
        """Index of values contained in this filegroup.

        Indexed on available scope.
        None designate a value not contained.
        """
        out = {name: c.contains for name, c in self.cs.items()}
        return out

    def __repr__(self):
        s = [self.__class__.__name__]
        s.append(f"Name: {self.name}")
        s.append(f"Root Directory: {self.root}")
        s.append(f"Pre-regex: {self.pregex}")
        s.append(f"Regex: {self.regex}")
        s.append('')

        s.append("Coordinates for scan:")
        for name, cs in self.cs.items():
            s1 = ['{} ({})'.format(name, cs.name)]
            s1.append(', {}'.format(['in', 'shared'][cs.shared]))
            if cs.has_data():
                s1.append(': {}, {}'.format(cs.get_extent_str(), cs.size))
            s.append(''.join(s1))
        return '\n'.join(s)

    def make_coord_scan(self, coords: List[Tuple[Coord, bool, str]]):
        """Add CoordScan objects.

        Each CoordScan is dynamically rebased
        from its parent Coord.

        :param coords: List of tuple containing the coordinate object,
            the shared flag, and the name of the coordinate infile.
        """
        self.cs = {}
        for coord, shared, name in coords:
            cs = dlcs.get_coordscan(self, coord, shared, name)
            self.cs.update({coord.name: cs})

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
        idx = 0
        regex = pregex
        for idx, match in enumerate(m):
            matcher = dlcs.Matcher(match, idx)
            self.cs[matcher.coord].add_matcher(matcher)
            regex = regex.replace(match.group(), '(' + matcher.rgx + ')')

        for name, cs in self.iter_shared(True).items():
            if len(cs.matchers) == 0:
                raise RuntimeError(f"'{name}' has no matcher in the pre-regex.")

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
                  mode: str = 'r', log_lvl: str = 'info') -> File:
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
        to_open = (any([cs.is_to_open() for cs in self.cs.values()])
                   or ('gen' in self.scan_attr and not self.scan_attr['gen'][1]))
        return to_open

    def scan_general_attributes(self, file: File):
        """Scan for general attributes."""
        func, scanned, kwargs = self.scan_attr['gen']
        if not scanned:
            log.debug('Scanning file for general attributes.')
            infos = func(self, file, **kwargs)
            log.debug("Found infos %s", list(infos.keys()))
            already_present = [info for info in infos if infos in self.vi.infos]
            for info in already_present:
                infos.pop(info)
            self.vi.set_infos(**infos)

            self.scan_attr['gen'][1] = True

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
            if 'gen' in self.scan_attr and not self.scan_attr['gen'][1]:
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

        Uses os.walk.
        Sort files alphabetically

        :raises RuntimeError: If no files are found.
        """
        # Using a generator should fast things up even though
        # less readable
        files = [os.path.relpath(os.path.join(root, file), self.root)
                 for root, _, files in os.walk(self.root)
                 for file in files]
        files.sort()

        if len(files) == 0:
            raise RuntimeError(f"No files were found in {self.root}")

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
        for elt in self.scan_attr:
            self.scan_attr[elt][1] = False
        # Reset CoordScan
        for cs in self.cs.values():
            if cs.is_to_scan():
                cs.scanned = False
                if cs.scan_attributes_func is not None:
                    cs.scan_attr = True
                if 'manual' not in cs.scan:
                    cs.reset()
                elif cs.shared:
                    cs.matches = [[] for _ in range(len(cs.values))]
        self.found_file = False

        files = self.find_files()
        for file in files:
            self.scan_file(file)

        if not self.found_file:
            raise NameError("No file matching the regex found ({}, regex={})"
                            .format(self.name, self.regex))

        for cs in self.cs.values():
            cs.set_values()

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

            if cs.is_to_check() or cs.name == 'var':
                if len(cs.values) == 0:
                    raise ValueError("No values detected ({0}, {1})".format(
                        cs.name, self.name))
                cs.update_values(cs.values)

    def set_scan_gen_attrs_func(self, func: Callable[..., Dict], **kwargs: Any):
        """Set function for scanning general attributes.

        :param func: Function that recovers variables attributes in file.
            See scan_general_attributes_default() for a better
            description of the function interface.
        :param kwargs: [opt] Passed to the function.
        """
        self.scan_attr['gen'] = [func, False, kwargs]

    def set_scan_var_attrs_func(self, func: Callable[..., Dict], **kwargs: Any):
        """Set the function for scanning variables specific attributes.

        :param func: Function that recovers variables attributes in file.
            See scan_variables_attributes_default() for a better
            description of the function interface.
        :param kwargs: [opt] Passed to the function.
        """
        self.scan_attr['var'] = [func, False, kwargs]

    def apply_coord_selection(self):
        """Apply CoordScan selection."""
        for dim, key in self.selection.items():
            cs = self.cs[dim]
            if isinstance(key, KeyValue):
                key = Key(key.apply(cs))
            log.debug("Slicing '%s' in filegroup '%s' with indices %s",
                      dim, self.name, key.no_int())
            cs.slice(key.no_int())


def scan_general_attributes_default(fg: 'FilegroupLoad', file: File,
                                    **kwargs: Any) -> Dict[str, Any]:
    """Scan general attributes in file.

    :param file: Object to access file.
        The file is already opened by FilegroupSan.open_file().

    :returns: Dictionnary of attributes.
        {attribute name: attribute value}.
        Attributes are added to the VI.
    """
    raise NotImplementedError()


def scan_variables_attributes_default(fg: 'FilegroupLoad', file: File,
                                      **kwargs: Any) -> Dict[str, Dict[str, Any]]:
    """Scan variable specific attributes.

    :param file: Object to access file.
        The file is already opened by FilegroupScan.open_file().

    :returns: Attributes per variable.
        {variable name: {attribute name: value}}
        Attributes are added to the VI.
    """
    raise NotImplementedError()
