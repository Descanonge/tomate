"""Data files management.

Files containing the same variables and having the same filenames are
regrouped into a same Filegroup.
CoordScan help to scan files to see what coordinates
values they hold.

Contains
--------

Filegroup:
    Contain informations on files which share the same variables
    and filename structure.
    Scan files and keeps a correspondance of what file contains
    what coordinates.
    Manage pre-regex processing
"""

import os
import re

from typing import List

from data_loader.coord import Coord
import data_loader.coord_scan as dlcs


class FilegroupScan():
    """An ensemble of files.

    File which share the same variables, and filename structure.

    Parameters
    ----------
    root: str
        Data directory
    contains: List[str]
        Variables contained in this filegroup
    vi: VariablesInfo
    coords: List[[Coord, shared: bool]]
        Parent coordinates objects, and a bool indicating if the coordinate
        is shared accross files

    Attributes
    ----------
    root: str
        Data directory
    contains: List[str]
        Variables contained in this filegroup
    cs: List[Coord]
        Parent coordinates objects
    n_matcher: int
        Number of matchers in pre-regex
    pregex: str
        Pre-regex
    regex: str
        Regex, matchers have been replaced with regexes
    segments: List[str]
        Fragments of filename used for reconstruction,
        pair indices are replaced with matches
    """

    def __init__(self, root, contains, db, coords):
        self.root = root
        self.contains = contains
        self.db = db

        self.found_file = False
        self.n_matcher = 0
        self.segments = []

        self.regex = ""
        self.pregex = ""

        self.make_coord_scan(coords)

    def make_coord_scan(self, coords: List[Coord]):
        """Add CoordScan objects."""
        self.cs = {}
        for coord, shared in coords:
            cs = dlcs.get_coordscan(self, coord, shared)
            self.cs.update({coord.name: cs})

    def enum_shared(self, shared=None):
        """Iter through CoordScan objects."""
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

    def enum_scan(self, scan=None):
        """Iter through CoordScan objects."""
        cs = {}
        for name, c in self.cs.items():
            add = False
            if scan is None:
                add = True
            elif scan == "scannable":
                add = len(c.scan) > 0
            else:
                add = scan in c.scan

            if add:
                cs[name] = c

        return cs

    def add_scan_regex(self, pregex, replacements):
        """Specify the regex for scanning.

        Create a proper regex from the pre-regex.
        Find the matchers: replace them by the appropriate regex,
        store segments for easy replacement by the matches later.

        Parameters
        ----------
        pregex: str
            Pre-regex
        replacements: Dict
            dictionnary of matchers to be replaced by a constant
            The keys must match a matcher in the pre-regex


        Example
        -------
        pregex = "%(prefix)_%(time:value)"
        replacements = {"prefix": "SST"}
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

        self.n_matcher = idx + 1
        self.regex = regex
        self.pregex = pregex

    def scan_pregex(self, pregex):
        """Scan pregex for matchers."""
        regex = r"%\(([a-zA-Z]*):([a-zA-Z]*)(?P<cus>:custom=)?((?(cus)[^:]+:))(:?dummy)?\)"
        m = re.finditer(regex, pregex)
        return m

    def find_segments(self, m):
        """Find segments in filename.

        Store result.
        """
        sep = [0]
        n = len(m.groups())
        for i in range(n):
            sep.append(m.start(i+1))
            sep.append(m.end(i+1))

        s = m.string
        self.segments = [s[i:j]
                         for i, j in zip(sep, sep[1:]+[None])]

    def scan_file(self, filename: str):
        # TODO: pass file instead of filename if necessary
        """Scan a single filename."""
        m = re.match(self.regex, filename)
        # TODO: message to debug the regex

        filename = os.path.join(self.root, filename)

        # Discard completely non matching files
        if m is None:
            return

        self.found_file = True

        if len(self.segments) == 0:
            self.find_segments(m)

        for cs in self.enum_scan("scannable").values():
            cs.scan_file(m, filename)

    def scan_files(self, files: List[str]):
        """Scan files.

        files: list of strings
        """
        for file in files:
            self.scan_file(file)

        if not self.found_file:
            raise Exception("No file matching the regex found ({0}, regex={1})".format(
                self.contains, self.regex))

        for cs in self.enum_scan("scannable").values():
            if len(cs.values) == 0:
                raise Exception("No values detected ({0}, {1})".format(
                    cs.name, self.contains))
            cs.sort_values()
            cs.update_values(cs.values)
