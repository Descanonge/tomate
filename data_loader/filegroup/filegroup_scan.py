"""Manages scanning of data files.

Files containing the same variables and having the same filenames are
regrouped into a same Filegroup.
"""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


import logging
from typing import List

import os
import re

import data_loader.filegroup.coord_scan as dlcs
from data_loader.coordinates.variables import Variables
from data_loader.key import Keyring


log = logging.getLogger(__name__)


class FilegroupScan():
    """An ensemble of files.

    Files which share the same variables, and filename structure.
    This class manages the scanning part of filegroups.

    Parameters
    ----------
    root: str
        Root data directory containing all files.
    contains: List[str]
        Variables contained in this filegroup.
    db: DataBase or subclass
        Parent database.
    coords: List[ List[Coord, shared: bool] ]
        Parent coordinates objects, and a bool indicating if the coordinate
        is shared accross files.
    vi: VariablesInfo
        Global VariablesInfo instance.

    Attributes
    ----------
    root: str
        Root data directory containing all files.
    contains: List[str]
        Variables contained in this filegroup.
    db: DataBase or subclass
        Parent database.
    cs: Dict[str, CoordScan or subclass]
        Dictionnary of scanning coordinates,
        each dynamically inheriting from its
        parent Coord.
    pregex: str
        Pre-regex.
    regex: str
        Regex.
    segments: List[str]
        Fragments of filename used for reconstruction,
        pair indices are replaced with matches.
    vi: VariablesInfo
        Global VariablesInfo instance.
    scan_attr: bool
        If the variables attributes have to be scanned.
    scan_attributes: Callable
        Function used to scan variables attributes.
    scan_infos: Callable
        Function used to scan general attributes.
    """

    def __init__(self, root, variables, db, coords, vi,
                 variables_shared=False):
        self.root = root
        self.db = db
        self.vi = vi

        self.found_file = False
        self.n_matcher = 0
        self.segments = []

        self.regex = ""
        self.pregex = ""

        self.scan_attr = False
        self.scan_attributes_func = scan_attributes_default

        self.cs = {}
        if variables is None:
            variables = []
        if 'var' not in [c[0].name for c in coords]:
            variables_coord = Variables(variables)
            coords.insert(0, [variables_coord, variables_shared])
        self.make_coord_scan(coords)

        csv = self.cs['var']
        csv.vi = vi
        csv.set_values_default(variables)

        self.contains = {dim: [] for dim in self.cs}

    @property
    def variables(self):
        csv = self.cs['var']
        if csv.has_data():
            v = csv[:].tolist()
        else:
            v = []
        return v

    def __str__(self):
        s = [self.__class__.__name__]
        s.append("Contains: %s" % ', '.join(self.variables))

        s.append("Root Directory: %s" % self.root)
        s.append("Pre-regex: %s" % self.pregex)
        s.append("Regex: %s" % self.regex)
        s.append('')

        s.append("Coordinates for scan:")
        for name, cs in self.cs.items():
            s1 = ["\t%s " % name]
            s1.append(["(in)", "(shared)"][cs.shared])
            if cs.scanned:
                s1.append(" found %d values, kept %d" % (len(cs.values), cs.size))
            s.append(''.join(s1))
        return '\n'.join(s)

    def make_coord_scan(self, coords):
        """Add CoordScan objects.

        Each CoordScan is dynamically rebased
        from its parent Coord.

        Parameters
        ----------
        coords: List[[Coord, shared: bool]]
        """
        self.cs = {}
        for coord, shared, name in coords:
            cs = dlcs.get_coordscan(self, coord, shared, name)
            self.cs.update({coord.name: cs})

    def iter_shared(self, shared=None):
        """Iter through CoordScan objects.

        Parameters
        ----------
        shared: bool, optional
            To iterate only shared coordinates (shared=True),
            or only in coordinates (shared=False).
            If left to None, iter all coordinates.

        Returns
        -------
        Dict[str, CoordScan]
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

    def set_scan_regex(self, pregex, **replacements):
        """Specify the pre-regex.

        Create a proper regex from the pre-regex.
        Find the matchers: replace them by the appropriate regex,
        store segments for easy replacement by the matches later.

        Parameters
        ----------
        pregex: str
            Pre-regex.
        replacements: str
            Matchers to be replaced by a constant.
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
    def scan_pregex(pregex):
        """Scan pregex for matchers.

        Parameters
        ----------
        pregex: str
             Pre-regex.

        Returns
        -------
        Iterator[re.match]
        """
        regex = r"%\(([a-zA-Z]*):([a-zA-Z]*)(?P<cus>:custom=)?((?(cus)[^:]+:))(:?dummy)?\)"
        m = re.finditer(regex, pregex)
        return m

    def find_segments(self, m):
        """Find segments in filename.

        Store result.

        Parameters
        ----------
        m: Iterator[re.match]
            Matches of the pre-regex to find matchers.
        """
        sep = [0]
        n = len(m.groups())
        for i in range(n):
            sep.append(m.start(i+1))
            sep.append(m.end(i+1))

        s = m.string
        self.segments = [s[i:j]
                         for i, j in zip(sep, sep[1:]+[None])]

    def open_file(self, filename, mode='r', log_lvl='info'):
        """Open a file.

        Parameters
        ----------
        filename: str
            File to open.
        mode: str
            Mode for opening (read only, replace, append, ...)
        log_lvl: {'debug', 'info', 'warning'}
            Level to log the opening at.
        """
        raise NotImplementedError

    def close_file(self, file):
        """Close file.

        Parameters
        ----------
        file:
            File object.
        """
        raise NotImplementedError

    def is_to_open(self) -> bool:
        """Return if the current file has to be opened."""
        to_open = any([cs.is_to_open() for cs in self.cs.values()])
        return to_open

    def scan_attributes(self, file):
        """Scan for attributes.

        Parameters
        ----------
        file:
            File object.
        """
        try:
            infos = self.scan_attributes_func(self, file)
        except NotImplementedError:
            pass
        else:
            log.debug("Found infos %s", list(infos.keys()))
            self.vi.add_infos(**infos)
            self.scan_attr = False

    def scan_file(self, filename: str):
        """Scan a single filename.

        Match filename against regex.
        If first match, retrieve segments.

        If needed, open file.
        If not done already, scan attributes and infos.

        Scan per coordinate.

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
            if self.scan_attr:
                self.scan_attributes(file)

            for cs in self.cs.values():
                if cs.is_to_scan():
                    cs.scan_file(m, file)
        except:
            if file is not None:
                self.close_file(file)
            raise
        else:
            if file is not None:
                self.close_file(file)

    def find_files(self) -> List[str]:
        """Find files to scan.

        Uses os.walk.
        Sort files alphabetically

        Raises
        ------
        RuntimeError:
            If no files are found.
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

        Raises
        ------
        NameError
            If no file were found.
        ValueError
            If no values were detected.
        """
        for cs in self.cs.values():
            if cs.shared:
                cs.matches = []
            if cs.is_to_scan_values() and 'manual' not in cs.scan:
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
            if cs.is_to_scan_values():
                if len(cs.values) == 0:
                    raise ValueError("No values detected ({0}, {1})".format(
                        cs.name, self.variables))
            if cs.is_to_check():
                cs.update_values(cs.values)

    def set_scan_attributes_func(self, func):
        """Set function for scanning variables attributes.

        Parameters
        ----------
        func: Callable[[file, variables: List[str]], [Dict]]
            Function that recovers variables attributes in file.
            See filegroup_scan.scan_attributes_default() for a better
            description of the function interface.
        """
        self.scan_attr = True
        self.scan_attributes_func = func


def scan_attributes_default(fg, file):
    """Scan general attributes in file.

    Parameters
    ----------
    fg: FilegroupScan
    file:
        Object to access file.
        The file is already opened by FilegroupSan.open_file()

    Returns
    -------
    infos: Dict[str, Any]
        Dictionnary of attributes.
        {attribute name: attribute value}.
        Attribute is then set to a Coord object
        using Coord.set_attr(name, attr).
    """
    raise NotImplementedError("scan_infos was not set for (%s)" % fg.variables)
