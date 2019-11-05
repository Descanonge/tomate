"""Construct a database easily.

Contains
--------
VIConstructor
    Help creating a VariablesInfo
FGConstructor
    Help creating Filegroup objects.
    Start scanning.
"""

import warnings
import os

import numpy as np

from data_loader.variables_info import VariablesInfo
from data_loader.filegroup import Filegroup
from data_loader.coord import select_overlap


class VIConstructor():
    """Help creating a VariablesInfo.

    Attributes
    ----------
    var_list: List[[name: str, infos]]

    Examples
    --------
    vic = VIConstructor()

    name = "SST"
    infos = {"fullname": "Sea Surface Temperature",
             "unit": "deg C"}
    vic.add_var(name, infos)
    """

    def __init__(self):
        self.var_list = []

    def add_var(self, name, infos):
        """Add a variable.

        Stores arguments for creation later.

        Parameters
        ----------
        name: str
            Variable name
        infos: Dict[info name: str, values: Any]
            Infos for this variable
        """
        self.var_list.append([name, infos])

    def make_vi(self):
        """Create the vi.

        Returns
        -------
        vi: VariablesInfo
        """
        names = [z[0] for z in self.var_list]
        infos = {z[0]: z[1] for z in self.var_list}

        vi = VariablesInfo(names, infos)

        return vi


class FGConstructor():
    """Helps creating Filegroup objects.

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
    vi: VariablesInfo
    filegroups: List[Filegroup]
    """

    def __init__(self, root, coords, vi):
        self.root = root
        self.coords = dict(zip([c.name for c in coords], coords))
        self.vi = vi
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

    def add_fg(self, contains, coords):
        """Add filegroup.

        Parameters
        ----------
        contains: List[str]
            list of variables contained in this grouping
            of files
        coords: List[[Coord, inout: str]]
            coordinates used in this grouping of files.
            list of tuples of the coordinate name and a inout flag
        """
        fg = Filegroup(self.root, contains, self.vi, coords)
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

    def set_scan_in_file(self, func, *coords):
        """Set function for scanning coordinates values in file.

        Parameters
        ----------
        func: Callable[[CoordScan, filename: str, values: List[float]],
                       values: List[float], in_idx: List[int]]
        *coords: List[Coord]
            Coordinate to apply this function for.
            If None, all coordinates with flag in*.
        """

        fg = self.current_fg

        if not coords:
            coords = list(fg.enum(inout="in*"))

        self.current_fg.set_scan_in_file_func(func, *coords)

    def set_scan_filename(self, func, *coords):
        """Set function for scanning coordinates values in filename.

        Parameters
        ----------
        func: Callable[[CoordScan, re.match], values: List[float]]
            Function that recover values from filename
        *coords: List[Coord]
            Coordinate to apply this function for.
        If None, all coordinates with flag *out.
        """
        fg = self.current_fg

        if not coords:
            coords = list(fg.enum(inout="*out"))

        self.current_fg.set_scan_filename_func(func, *coords)

    def set_coord_const_values(self, coord, values):
        """Set coordinates values manually.

        Parameters
        ----------
        coord: str
            Coordinate name
        values: Sequence[float]
        """
        fg = self.current_fg
        cs = fg.cs[coord]
        if cs.inout in cs.SCAN:
            warnings.warn("{cs.name} has a scannable flag. "
                          "Values set manually could be overwritten.")

        self.current_fg.cs[coord].set_values(values)

    def scan_files(self):
        """Scan files.

        Creates coordinates values.
        """
        files = []
        for root, _, file in os.walk(self.root):
            root = os.path.relpath(root, self.root)
            for f in file:
                files.append(os.path.join(root, f))

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
        ValueError
            If coordinates have different values across filegroups.
        """
        for name, coord in self.coords.items():
            coords = []
            for fg in self.filegroups:
                for name_cs, cs in fg.enum("scan").items():
                    if name == name_cs:
                        coords.append(cs)

            overlap = select_overlap(*coords)
            for i, cs in enumerate(coords):
                sl = overlap[i]
                if sl[0] != 0 or sl[1] != len(cs.values):
                    mess = ("({:s}) does not have the same range across"
                            " all filegroups. A common range is taken. "
                            "{:g} - {:g}").format(cs.name,
                                                  cs.values[sl[0]],
                                                  cs.values[sl[1]-1])
                    warnings.warn(mess, stacklevel=2)

                coords[i].slice(slice(*overlap[i]))

            # Select the first coordinate found in the filegroups
            # with that name
            coords[0].assign_values()

            # Check that all filegroups have same values
            for cs in coords:
                if np.any(cs.values - cs.coord[:] > threshold):
                    raise ValueError(("({:s}) has different values across "
                                      "filegroups.".format(name)))

    def make_filegroups(self):
        """Retrieve the list of filegroups.

        Scan files
        Select overlap coordinates

        Returns
        -------
        filegroups: List[Filegroup]
        """
        self.scan_files()
        self.check_values()

        return self.filegroups
