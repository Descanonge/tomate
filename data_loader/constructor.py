"""Construct a database easily.

Contains
--------
Constructor
    Help creating Filegroup objects.
    Start scanning.
"""

import logging
import os

import numpy as np

from data_loader.variables_info import VariablesInfo
from data_loader.coord import select_overlap

log = logging.getLogger(__name__)



class Constructor():
    """Helps creating a database object.

    Parameters
    ----------
    root: str
        Root directory of all files
    coords: List[Coord]
        Coordinates
    vi: VariablesInfo

    Attributes
    ----------
    root: str
        Root directory of all files
    coords: Dict[name: str, Coord]
    filegroups: List[Filegroup]
    """

    def __init__(self, root, coords):
        self.root = root
        self.coords = dict(zip([c.name for c in coords], coords))
        self.vi = VariablesInfo()

        self.filegroups = []

    @property
    def current_fg(self):
        """Current filegroup.

        Last filegroup added.

        Returns
        -------
        fg: Filegroup
        """
        return self.filegroups[-1]

    def add_variable(self, variable, info=None):
        """Add variable along with info / attribute.

        Parameters
        ----------
        variable: str
            Id of the variable
        """
        if info is None:
            info = {}
        self.vi.add_variable(variable, info)

    def add_kwargs(self, **kwargs):
        """Add attributes to the vi."""
        self.vi.add_kwargs(**kwargs)

    def add_fg(self, fg_type, contains, coords, *args, **kwargs):
        """Add filegroup.

        Parameters
        ----------
        contains: List[str]
            list of variables contained in this grouping
            of files
        coords: List[[Coord, shared: str or bool]]
            coordinates used in this grouping of files.
            list of tuples of the coordinate name and a inout flag
        """
        shared_corres = {'in': False, 'shared': True}
        for i, [c, shared] in enumerate(coords):
            if not isinstance(shared, bool):
                if shared not in shared_corres:
                    raise ValueError("Shared must be bool or %s\n(%s, %s)"
                                     % (list(shared_corres.keys()),
                                        contains, c.name))
            if shared == "shared":
                shared = True
            elif shared == "in":
                shared = False
            coords[i][1] = shared

        fg = fg_type(self.root, contains, None, coords, self.vi, *args, **kwargs)
        self.filegroups.append(fg)

    def set_fg_regex(self, pregex, replacements):
        """Add filegroup with a regex scanning method.

        Parameters
        ----------
        pregex: str
            pre-regex
        replacements: Dict[name: str, replacement: Any]
            Constants to replace in pre-regex

        Examples
        --------
        fgc.set_fg_regex("%(prefix)_%(time:year)",
                         {"prefix": "SST"})
        """
        self.current_fg.add_scan_regex(pregex, replacements)

    def set_scan_in_file_func(self, func, *coords):
        """Set function for scanning coordinates values in file.

        Parameters
        ----------
        func: Callable[[CoordScan, filename: str, values: List[float]],
                       values: List[float], in_idx: List[int]]
        coords: List[Coord]
            Coordinate to apply this function for.
        """
        fg = self.current_fg
        for name in coords:
            cs = fg.cs[name]
            cs.set_scan_in_file_func(func)

    def set_scan_filename_func(self, func, *coords, **kwargs):
        """Set function for scanning coordinates values in filename.

        Parameters
        ----------
        func: Callable[[CoordScan, re.match], values: List[float]]
            Function that recover values from filename
        coords: List[Coord]
            Coordinate to apply this function for.
        """
        fg = self.current_fg
        for name in coords:
            cs = fg.cs[name]
            cs.set_scan_filename_func(func, **kwargs)

    def set_scan_manual(self, coord, values, in_idx=None):
        """Set coordinate values manually."""

        if in_idx is None:
            in_idx = [None for _ in range(len(values))]

        fg = self.current_fg
        cs = fg.cs[coord]
        cs.set_scan_manual(values, in_idx)

        if cs.scan:
            log.warning("%s has a scannable flag. "
                        "Values set manually could be overwritten.", cs.name)

    def set_scan_coords_attributes_func(self, func, *coords):
        """Set a function for scanning coordinate attributes."""
        fg = self.current_fg
        for name in coords:
            cs = fg.cs[name]
            cs.set_scan_attributes(func)

    def set_scan_variables_attributes_func(self, func):
        """Set a function for scanning variables attributes to current fg."""
        fg = self.current_fg
        fg.set_scan_attributes_func(func)

    def set_coord_descending(self, *coords):
        """Set a coordinate as descending in the filegroup.

        Parameters
        ----------
        coords: List of str
        """
        fg = self.current_fg
        for name in coords:
            fg.cs[name].set_idx_descending()

    def scan_files(self):
        """Scan files.

        Creates coordinates values.

        Raises
        ------
        RuntimeError:
            If no files are found
        """
        files = []
        for root, _, file in os.walk(self.root):
            root = os.path.relpath(root, self.root)
            for f in file:
                files.append(os.path.join(root, f))
        files.sort()

        if len(files) == 0:
            raise RuntimeError("No files were found in {:s}".format(self.root))

        for fg in self.filegroups:
            fg.scan_files(files)

    def check_values(self, threshold=1e-5):
        """Check and select overlap.

        Select a common range across filegroups coordinates.
        Check if coordinates have the same values across filgroups.

        Parameters
        ----------
        threshold: float = 1e-5
            Threshold used for float comparison

        Raises
        ------
        IndexError
            If coordinates have different lengthes across filegroup.
        ValueError
            If coordinates have different values across filegroups
            (above `threshold`).
        """
        for name, coord in self.coords.items():
            coords = []
            for fg in self.filegroups:
                for name_cs, cs in fg.enum_scan("scannable").items():
                    if name == name_cs:
                        coords.append(cs)

            overlap = select_overlap(*coords)
            cut = ""
            for i, cs in enumerate(coords):
                sl = overlap[i].indices(cs.size)
                if sl[0] != 0 or sl[1] != len(cs.values):
                    cut += "\n" + str(cs.filegroup.contains) + " " + cs.get_extent_str()

                cs.slice(overlap[i])
                cs.slice_total = overlap[i]

            # Select the first coordinate found in the filegroups
            # with that name
            coords[0].assign_values()

            if len(cut) > 0:
                mess = ("'%s' does not have the same range across"
                        " all filegroups. A common range is taken. %s")
                log.warning(mess+cut, name, coord.get_extent_str())

            # Check length
            for cs in coords:
                if cs.size != cs.coord.size:
                    raise IndexError(("'{0}' has different lengthes across "
                                      "filegroups. ({1} has {2}, expected {3})").format(
                                          name,
                                          cs.filegroup.contains, cs.size, cs.coord.size))

            # Check that all filegroups have same values
            for cs in coords:
                if np.any(cs[:] - cs.coord[:] > threshold):
                    raise ValueError(("'{:s}' has different values across "
                                      "filegroups.").format(name))

    def check_regex(self):
        """Check if a pregex has been added where needed.

        Raises
        ------
        RuntimeError:
            If regex is empty and there is at least a out coordinate.
        """
        for fg in self.filegroups:
            coords = list(fg.enum_shared(True))
            if len(coords) > 0 and fg.regex == '':
                mess = ("Filegroup is missing a regex.\n"
                        "Contains: {0}\nCoordinates: {1}").format(
                            fg.contains, coords)
                raise RuntimeError(mess)

    def make_database(self, db_type):
        """Create database instance.

        Scan files
        Select overlap coordinates
        """
        self.check_regex()
        self.scan_files()
        self.check_values()
        dt = db_type(self.root, self.filegroups, self.vi, *self.coords.values())
        return dt
