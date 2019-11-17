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
import data_loader.coord_scan as dlcs


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
            #TODO: Move RB in coord_scan.py
            CoordScanRB = type('CoordScanRB', (type(coord),), dict(dlcs.CoordScan.__dict__))

            if inout.endswith("out"):
                CoordScanInOutRB = type('CoordScanInOutRB', (CoordScanRB,),
                                        dict(dlcs.CoordScanInOut.__dict__))
                self.cs.update({coord.name: CoordScanInOutRB(self, CoordScanRB, coord, inout)})
            elif inout == "in":
                CoordScanInRB = type('CoordScanInRB', (CoordScanRB,),
                                        dict(dlcs.CoordScanIn.__dict__))
                self.cs.update({coord.name: CoordScanInRB(self, CoordScanRB, coord)})
            else:
                self.cs.update({coord.name: CoordScanRB(self, CoordScanRB, coord, inout)})

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
            matcher = dlcs.Matcher(string[2:-1], idx)

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
                raise Exception("No values detected ({0}, {1})".format(
                    cs.name, cs.filegroup.contains))
            cs.sort_values()
            cs.update_values(cs.values)

    def get_commands(self, var_list, keys):
        """Retrieve filenames.

        Recreate filenames from matches.

        Parameters
        ----------
        var_list: List[str]
            List of variables names
        keys: Dict[str, NpIdx]
            Dict of coord keys to load from the data
            available
            Keys are passed to numpy arrays

        Returns
        -------
        filename: str
            Filename to load
        var_list: List[str]
        keys: Dict[str, NpIdx]
            Keys for the whole data
        keys_in: Dict[str, NpIdx]
            Keys to load in the filename
        keys_slice: Dict[str, NpIdx]
            Keys of the slice that is going to be loaded, for
            that filename, and in order.
        """
        # Retrieve matches, indexes of regexes, and
        # in-file indexes.
        matches = []
        rgx_idxs = []
        in_idxs = []
        for name, cs in self.enum("*out").items():
            key = keys[name]
            match = []
            rgx_idx_matches = []
            for i, rgx in enumerate(cs.matchers):
                match.append(cs.matches[key, i])
                rgx_idx_matches.append(rgx.idx)

            # Matches are stored by regex index, we
            # need to transpose to have a list by filename
            match = np.array(match)
            matches.append(match.T)
            in_idxs.append(cs.in_idx[key])
            rgx_idxs.append(rgx_idx_matches)

        # Number of matches by out coordinate for looping
        lengths = []
        for i_c, _ in enumerate(matches):
            lengths.append(len(matches[i_c]))

        commands = []
        # Imbricked for loops for all out coords
        for m in itertools.product(*(range(z) for z in lengths)):

            # Reconstruct filename
            seg = self.segments.copy()
            for i_c, cs in enumerate(self.enum("*out").keys()):
                idx_rgx_matches = rgx_idxs[i_c]
                for i, rgx_idx in enumerate(idx_rgx_matches):
                    seg[2*rgx_idx+1] = matches[i_c][m[i_c]][i]
            filename = "".join(seg)

            # Find keys
            keys_slice = {}
            keys_in = {}
            i_c = 0
            for name, cs in self.enum().items():
                if cs.inout == "in":
                    keys_slice[name] = slice(None, None)
                    keys_in[name] = keys[name]
                elif cs.inout.endswith("out"):
                    keys_slice[name] = m[i_c]
                    keys_in[name] = in_idxs[i_c][m[i_c]]
                    i_c += 1

            commands.append([filename, var_list, keys_in, keys_slice])

        return commands

    # TODO: no out coords ?
    # TODO: inout: pb if coords ends mid file
