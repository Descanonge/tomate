"""Manages scanning of data files."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


import logging
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, TYPE_CHECKING

import os
import re

import data_loader.filegroup.coord_scan as dlcs

from data_loader.coordinates.coord import Coord
from data_loader.custom_types import File
from data_loader.filegroup.coord_scan import CoordScan
from data_loader.variables_info import VariablesInfo
if TYPE_CHECKING:
    from data_loader.filegroup.filegroup_load import FilegroupLoad
    from data_loader.data_base import DataBase

log = logging.getLogger(__name__)


class FilegroupScan():
    """Manages set of files on disk.

    Files which share the same structure and filenames.
    This class manages the scanning part of filegroups.

    :param root: Root data directory containing all files.
    :param db: Parent database.
    :param coords: Parent coordinates objects, a bool indicating if the coordinate
        is shared accross files, and their name inside files.
    :param vi: Global VariablesInfo instance.
    :param name: [opt] Name of the filegroup.

    Attributes
    ----------
    root: str
        Root data directory containing all files.
    db: DataBase or subclass
        Parent database.
    vi: VariablesInfo
        Global VariablesInfo instance.
    name: str
        Name of the filegroup.
    cs: Dict[str, CoordScan or subclass]
        Dictionnary of scanning coordinates,
        each dynamically inheriting from its parent Coord.
    pregex: str
        Pre-regex.
    regex: str
        Regex.
    segments: List[str]
        Fragments of filename used for reconstruction,
        pair indices are replaced with matches.
    scan_attr: Dict[type: {'gen' | 'var'}, [Callable, scanned:bool, kwargs: Dict]]
        Functions to call to scan variables specific
        attributes or general attributes.
    contains: Dict[dim:str, Array]
        For each dimension, for each value in the available
        scope, the index of that value in the filegroups CS.
        If that value is not contained in this filegroup, the
        index is None.
    """

    def __init__(self, root: str,
                 db: 'DataBase',
                 coords: List[Tuple[Coord, bool, str]],
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
        self.make_coord_scan(coords)

        self.contains = {dim: [] for dim in self.cs}

    @property
    def variables(self) -> List[str]:
        """List of variables contained in this filegroup."""
        csv = self.cs['var']
        if csv.has_data():
            v = csv[:].tolist()
        else:
            v = []
        return v

    def __str__(self):
        s = [self.__class__.__name__]
        s.append("Name: %s" % self.name)
        s.append("Root Directory: %s" % self.root)
        s.append("Pre-regex: %s" % self.pregex)
        s.append("Regex: %s" % self.regex)
        s.append('')

        s.append("Coordinates for scan:")
        for name, cs in self.cs.items():
            s1 = ['%s (%s)' % (name, cs.name)]
            s1.append(', %s' % ['in', 'shared'][cs.shared])
            if cs.has_data():
                s1.append(': %s, %s' % (cs.get_extent_str(), cs.size))
            s.append(''.join(s1))
        return '\n'.join(s)

    def __repr__(self):
        return '\n'.join([super().__repr__(), str(self)])

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
                raise RuntimeError("'%s' has no matcher in the pre-regex." % name)

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
                   or not self.scan_attr.get('gen', True))
        return to_open

    def scan_general_attributes(self, file: File):
        """Scan for general attributes."""
        func, scanned, kwargs = self.scan_attr['gen']
        if not scanned:
            log.debug('Scanning file for general attributes.')
            infos = func(self, file, **kwargs)
            log.debug("Found infos %s", list(infos.keys()))
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
        self.found_file = True

        if len(self.segments) == 0:
            self.find_segments(m)

        file = None
        if self.is_to_open():
            file = self.open_file(filename, mode='r', log_lvl='debug')

        try:
            if not self.scan_attr.get('gen', True):
                self.scan_general_attributes(file)

            for cs in self.cs.values():
                cs.scan_attributes(file)
                cs.scan_file(m, file)
        except:
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
            raise RuntimeError("No files were found in %s" % self.root)

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
        # Reset CoordScan
        for cs in self.cs.values():
            if cs.is_to_scan():
                if 'manual' not in cs.scan:
                    cs.reset()
                elif cs.shared:
                    cs.matches = [[] for _ in range(len(cs.values))]

        files = self.find_files()
        for file in files:
            self.scan_file(file)

        if not self.found_file:
            raise NameError("No file matching the regex found ({0}, regex={1})".format(
                self.variables, self.regex))

        for cs in self.cs.values():
            cs.set_values()
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
