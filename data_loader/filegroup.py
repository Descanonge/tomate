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
import itertools

from typing import List, Dict

import numpy as np

from data_loader.coord import Coord
from data_loader.coord_scan import (CoordScan,
                                    CoordScanIn,
                                    CoordScanInOut,
                                    Matcher)


class Filegroup():
    """An ensemble of files.

    File which share the same variables, and filename structure.

    Parameters
    ----------
    root: str
        Data directory
    contains: List[str]
        Variables contained in this filegroup
    vi: VariablesInfo
    coords: List[Coord]
        Parent coordinates objects

    Attributes
    ----------
    root: str
        Data directory
    contains: List[str]
        Variables contained in this filegroup
    coords: List[Coord]
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
    SCAN: List[str]
        Inout flags to be scanned
    """

    # List of inout flag to be scanned
    SCAN = ["in", "inout", "out"]

    def __init__(self, root, contains, vi, coords):
        self.root = root
        self.contains = contains
        self._vi = vi

        self.n_matcher = 0
        self.segments = []

        self.regex = ""
        self.pregex = ""

        self.make_coord_scan(coords)

    def make_coord_scan(self, coords: List[Coord]):
        """Add CoordScan objects."""
        self.cs = {}
        for coord, inout in coords:
            if inout.endswith("out"):
                self.cs.update({coord.name: CoordScanInOut(coord, inout)})
            elif inout == "in":
                self.cs.update({coord.name: CoordScanIn(coord)})
            else:
                self.cs.update({coord.name: CoordScan(coord, inout)})

    def enum(self, inout: str = "*") -> Dict:
        """Iter through CoordScan objects.

        Parameters
        ----------
        inout: str, {'in', 'out', 'inout', '*out', 'in*',
                     '*', 'scan'}
            CoordScan to iterate through with the specified flag
        """
        cs = {}
        for coord, c in self.cs.items():
            add = False
            if inout == "*":
                add = True
            elif inout == "in*":
                if c.inout.startswith("in"):
                    add = True
            elif inout == "*out":
                if c.inout.endswith("out"):
                    add = True
            elif inout == "scan":
                if c.inout in self.SCAN:
                    add = True
            else:
                if c.inout == inout:
                    add = True

            if add:
                cs.update({coord: c})

        return cs

    def set_scan_in_file_func(self, func, *coords):
        """Set the function used for scanning in files.

        Parameters
        ----------
        func: Callable[[CoordScan, filename: str, values: List[float]],
                       values: List[float], in_idx: List[int]]
        *coords: List[Coord]
            Coordinate to apply this function for.
            If None, all coordinates with flag in*.

        Raises
        ------
        AttributeError
            If the coordinate flag is wrong.
        """
        for name in coords:
            cs = self.cs[name]
            if not cs.inout.startswith('in'):
                raise AttributeError(("{:s} has flag {:s}, ").format(
                    name, cs.inout))
            cs.set_scan_in_file_func(func)

    def set_scan_filename_func(self, func, *coords):
        """Set the function used for scanning filenames.

        Parameters
        ----------
        func: Callable[[CoordScan, re.match], values: List[float]]
            Function that recover values from filename
        coords: List[Coord]
            Coordinate to apply this function for.
            If None, all coordinates with flag \*out.

        Raises
        ------
        AttributeError
            If the coordinate flag is wrong.
        """
        for name in coords:
            cs = self.cs[name]
            if not cs.inout.endswith('out'):
                raise AttributeError(("{:s} has flag {:s}, ").format(
                    name, cs.inout))
            cs.set_scan_filename_func(func)

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

        m = re.finditer(r"%\([a-zA-Z]*(:[a-zA-Z]*)?(:dummy)?\)", pregex)

        # Separations between segments
        sep = [0]
        regex = pregex
        idx = 0
        for idx, match in enumerate(m):
            string = match.group()
            matcher = Matcher(string[2:-1], idx)

            self.cs[matcher.coord].add_matcher(matcher)
            regex = regex.replace(string, matcher.get_regex())

            sep.append(match.start())
            sep.append(match.end())

        self.segments = [pregex.replace('\\', '')[i:j]
                         for i, j in zip(sep, sep[1:]+[None])]

        self.n_matcher = idx + 1
        self.regex = regex
        self.pregex = pregex

    def scan_file(self, filename: str):
        # TODO: pass file instead of filename if necessary
        """Scan a single filename."""
        m = re.match(self.regex, filename)

        filename = os.path.join(self.root, filename)

        # Discard completely non matching files
        if m is None:
            return

        for cs in self.enum("scan").values():
            cs.scan_file(m, filename)

    def scan_files(self, files: List[str]):
        """Scan files.

        files: list of strings
        """
        for file in files:
            self.scan_file(file)

        for cs in self.enum(inout="scan").values():
            if len(cs.values) == 0:
                raise Exception("No values detected ({:s})".format(cs.name))
            cs.sort_values()
            cs.update_values(cs.values)

    def get_filenames(self, var_list, keys):
        """Retrieve filenames.

        Recreate filenames from matches.

        Parameters
        ----------
        var_list: List[str]
            list of variables names
        keys: Dict[str, NpIdx]
            dict of coord keys to load
            Keys are passed to numpy arrays
        """
        files = []
        matches = []
        in_idxs = []
        idxs = []
        for coord, cs in self.enum("*out").items():
            cs = self.cs[coord]
            key = keys[coord]
            match = []
            idx = []
            for i, rgx in enumerate(cs.matchers):
                match.append(cs.matches[key, i])
                idx.append(rgx.idx)
            match = np.array(match)
            matches.append(match.T)
            in_idxs.append(cs.in_idx[key])
            idxs.append(idx)

        L = []
        for i_c, _ in enumerate(matches):
            L.append(len(matches[i_c]))

        for m in itertools.product(*(range(z) for z in L)):
            seg = self.segments.copy()
            keys_ = keys.copy()
            for i_c, coord in enumerate(self.enum("*out").keys()):
                idx = idxs[i_c]
                for i in range(len(idx)):
                    seg[2*idx[i]+1] = matches[i_c][m[i_c]][i]
                keys_.update({coord: in_idxs[i_c][m[i_c]]})

            file = "".join(seg)
            files.append([file, var_list, keys_])

        return files
