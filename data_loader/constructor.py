"""Construct a database easily."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


import logging
import os
import inspect

from data_loader.variables_info import VariablesInfo
from data_loader.coordinates.coord import select_overlap
from data_loader.accessor import Accessor


log = logging.getLogger(__name__)


class Constructor():
    """Helps creating a database object.

    Start the scanning process, and check if
    results are coherent across filegroups.

    Parameters
    ----------
    root: str
        Root directory of all files.
    coords: List[Coord]
        Coordinates, in the order the data should be kept.

    Attributes
    ----------
    root: str
        Root directory of all files.
    coords: Dict[str, Coord]
        Coordinates, in the order the data should be kept.
    filegroups: List[Filegroup]
        Filegroups added so far.
    vi: VariablesInfo
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

    def add_variable(self, variable, **attributes):
        """Add variable along with attributes.

        Parameters
        ----------
        variable: str
            Id of the variable.
        attributes: optional
            Variable specific information.

        Examples
        --------
        >>> name = "SST"
        ... attrs = {'fullname': 'Sea Surface Temperature',
        ...          'max_value': 40.}
        ... cstr.add_variable(name, **attrs)
        """
        self.vi.add_variable(variable, **attributes)

    def add_infos(self, **infos):
        """Add information to the vi.

        Add not variable-specific attributes to the vi.

        Parameters
        ----------
        infos: Dict[Any]

        Examples
        --------
        >>> cstr.add_infos(altimetry_data=['SSH', 'U', 'V'])
        """
        self.vi.add_infos(**infos)

    def add_filegroup(self, fg_type, contains, coords, root=None, **kwargs):
        """Add filegroup.

        Parameters
        ----------
        fg_type: FilegroupLoad subclass
            Class of filegroup to add. Dependant on the file-format.
        contains: List[str]
            List of variables contained in this grouping
            of files.
        coords: List[Coord, shared: str or bool]
            Coordinates used in this grouping of files.
            Each element of the list is a length 2 tuple of
            the coordinate name, and a shared flag.
            The flag can be 'shared' or 'in'.
        coords: str
            Subfolder from root.
        kwargs
            Passed to the fg_type initializator.

        Examples
        --------
        >>> add_filegroup(FilegroupNetCDF, ['Chla', 'Chla_error'],
        ...               [['lat', 'in'], ['lon', 'in'], ['time', 'shared']])
        """
        shared_corres = {'in': False, 'shared': True}
        for i, [c, shared] in enumerate(coords):
            if not isinstance(shared, bool):
                if shared not in shared_corres:
                    raise ValueError("Shared must be bool or %s\n(%s, %s)"
                                     % (list(shared_corres.keys()),
                                        contains, c.name))
                shared = shared_corres[shared]
            coords[i][1] = shared

        if root is None:
            root = ''
        root = os.path.join(self.root, root)

        if contains is None:
            contains = []
        elif isinstance(contains, str):
            contains = [contains]
        contains = list(contains)

        fg = fg_type(root, contains, None, coords, self.vi, **kwargs)
        self.filegroups.append(fg)

    def set_fg_regex(self, pregex, replacements=None):
        """Add the pre-regex to the current filegroup.

        Parameters
        ----------
        pregex: str
            Pre-regex.
        replacements: Dict[name: str, replacement: Any], optional
            Constants to replace in pre-regex.

        Examples
        --------
        >>> cstr.set_fg_regex("%(prefix)_%(time:year)",
        ...                   {"prefix": "SST"})
        """
        if replacements is None:
            replacements = {}
        self.current_fg.add_scan_regex(pregex, **replacements)

    def set_variables_infile(self, *variables, **kw_variables):
        """Set variables index in the file.

        This information will be transmitted to the filegroup
        when loading.
        It can be a integer or a string (to indicate a name)
        under which the variable is found in file.
        If not specified, None value is assigned, and the
        filegroup subclass should manage this case.

        This is similar to using Constructor.set_scan_manual()
        for the 'Variables' coordinate.

        Parameters
        ----------
        variables: int, str, None, optional
            Argument in the order of variables indicated
            when adding the last filegroup.
        kw_variables: int, str, None, optional
            Argument name is the variable name.
            Takes precedence over `variables`.

        Examples
        --------
        >>> cstr.set_variables_infile('SST', 'CHL')

        >>> cstr.set_variables_infile(sst='SST')
        """
        fg = self.current_fg
        for i, inf in enumerate(variables):
            var = fg.contains[i]
            if var not in kw_variables:
                kw_variables[var] = inf

        cs = fg.cs['var']
        values = fg.contains.copy()
        in_idx = [kw_variables.get(var, None) for var in fg.contains]
        cs.set_scan_manual(values, in_idx)

    def set_scan_in_file(self, func, *coords):
        """Set function for scanning coordinates values in file.

        Parameters
        ----------
        func: Callable[[CoordScan, file, values: List[float]],
                       [values: List[float], in_idx: List[int]]]
            Function that captures values and in-file index
        coords: List of str
            Coordinates to apply this function for.

        Notes
        -----
        See coord_scan.scan_in_file_default() for a better description of
        the function interface.
        """
        fg = self.current_fg
        for name in coords:
            cs = fg.cs[name]
            if 'manual' in cs.scan:
                log.warning("Values set manually will be overriden for '%s' from %s",
                            cs.name, fg.contains)
            cs.set_scan_in_file_func(func)

    def set_scan_filename(self, func, *coords, **kwargs):
        """Set function for scanning coordinates values from filename.

        Parameters
        ----------
        func: Callable[[], [values: List[float], in_idx: List[int]]
            Function that recover values from filename.
        coords: List[Coord]
            Coordinate to apply this function for.

        Notes
        -----
        See coord_scan.scan_filename_default() for a better description of
        the function interface.
        """
        fg = self.current_fg
        for name in coords:
            cs = fg.cs[name]
            if 'manual' in cs.scan:
                log.warning("Values set manually will be overriden for '%s' from %s",
                            cs.name, fg.contains)
            cs.set_scan_filename_func(func, **kwargs)

    def set_scan_manual(self, coord, values, in_idx=None):
        """Set coordinate values manually.

        Values will still be checked for consistency with
        others filegroups.

        Parameters
        ----------
        coord: str
            Coordinate to set the values for.
        values: List[float]
            Values for the coordinate.
        in_idx: List[int], optional
            Values of the in-file index.
        """
        if in_idx is None:
            in_idx = [None for _ in range(len(values))]

        fg = self.current_fg
        cs = fg.cs[coord]
        cs.set_scan_manual(values, in_idx)

    def set_scan_coords_attributes(self, func, *coords):
        """Set a function for scanning coordinate attributes.

        Parameters
        ----------
        func: Callable[[file], [Dict[str, Any]]]
            Function that recovers coordinate attribute in file.
        coords: str
            Coordinates to apply this function for.

        Notes
        -----
        See coord_scan.scan_attributes_default() for a better description
        of the function interface.
        """
        fg = self.current_fg
        for name in coords:
            cs = fg.cs[name]
            cs.set_scan_attributes_func(func)

    def set_scan_general_attributes(self, func):
        """Set a function for scanning general data attributes.

        Parameters
        ----------
        func: Callable[[file],
                       [Dict[info name, Any]]]

        Notes
        -----
        See filegroup_scan.scan_attributes_default() for a better
        description of the function interface.
        """
        fg = self.current_fg
        fg.set_scan_attributes_func(func)

    def set_coord_descending(self, *coords):
        """Set coordinates as descending in the filegroup.

        Parameters
        ----------
        coords: List[str]
        """
        fg = self.current_fg
        for name in coords:
            cs = fg.cs[name]
            if cs.shared:
                log.warning("%s '%s' is shared, setting it index descending"
                            " will have no impact.", fg.contains, name)
            cs.set_idx_descending()

    def scan_files(self):
        """Scan files.

        Find coordinates values and eventually, in-file indices.
        """
        for fg in self.filegroups:
            fg.scan_files()

    def check_scan(self, threshold=1e-5):
        """Check scanned values are compatible accross filegroups.

        Select a common range across filegroups coordinates.
        Check if coordinates have the same values across filgroups.

        Parameters
        ----------
        threshold: float = 1e-5
            Threshold used for float comparison
        """
        for name in self.coords:
            coords = []
            for fg in self.filegroups:
                for name_cs, cs in fg.cs.items():
                    if cs.is_to_check() and name_cs == name:
                        coords.append(cs)

            check_range(coords)
            check_values(coords, threshold)

            # Select the first coordinate found in the filegroups
            # with that name
            coords[0].assign_values()

    def check_regex(self):
        """Check if a pregex has been added where needed.

        Raises
        ------
        RuntimeError:
            If regex is empty and there is at least a out coordinate.
        """
        for fg in self.filegroups:
            coords = list(fg.iter_shared(True))
            if len(coords) > 0 and fg.regex == '':
                mess = ("Filegroup is missing a regex.\n"
                        "Contains: {0}\nCoordinates: {1}").format(
                            fg.contains, coords)
                raise RuntimeError(mess)

    def make_data(self, dt_types, accessor=None, scan=True):
        """Create data instance.

        Check a regex is present in every filegroup.
        Scan files.
        Check coordinates for consistency across filegroups.
        Create database object from multiple subclasses of data.

        Parameters
        ----------
        dt_type: DataBase or subclass (or a list of)
            Database classes to use, in order of
            priority for method resolution (Methods and
            attributes of the first one in
            the list take precedence).

        Returns
        -------
        Data instance ready to use.

        See also
        --------
        create_data_class:
            Dynamically add inheritance to
            create a new data class.
        """
        if scan:
            self.check_regex()
            self.scan_files()
            self.check_scan()

        dt_class = create_data_class(dt_types, accessor)

        variables = list(self.vi.var)
        for fg in self.filegroups:
            variables += fg.contains
        for var in variables:
            if var not in self.vi:
                self.vi.add_variable(var)

        dt = dt_class(self.root, self.filegroups, self.vi, *self.coords.values())
        return dt


def check_range(coords):
    """Check coords range, slice if needed.

    Parameters
    ----------
    coords: List[CoordScan]
         CoordScan of different filegroups, linked to the same coordinate.
    """
    overlap = select_overlap(*coords)
    cut = False
    for i, cs in enumerate(coords):
        level = 'DEBUG'
        sl = overlap[i].indices(cs.size)
        if sl[0] != 0 or sl[1] != len(cs.values):
            cut = True
            level = 'WARNING'

        log.log(getattr(logging, level),
                "%s '%s' has range %s",
                cs.filegroup.contains, cs.name, cs.get_extent_str())

        cs.slice(overlap[i])

    if cut:
        cs = coords[0]
        log.warning("'%s' does not have the same range across"
                    " all filegroups. A common range is taken. %s",
                    cs.name, cs.get_extent_str())


def check_values(coords, threshold):
    """Check coords values, keep values in common.

    Parameters
    ----------
    coords: List[CoordScan]
         CoordScan of different filegroups, linked to the same coordinate.

    Raises
    ------
    IndexError
        If a coordinate has no common values across filegroups.
    """
    sizes = [cs.size for cs in coords]
    for i in range(len(coords) - 1):
        c1 = coords[i]
        c2 = coords[i+1]
        i1, i2 = c1.get_collocated_float(c2, threshold)
        c1.slice(i1)
        c2.slice(i2)

    for cs, size in zip(coords, sizes):
        if  cs.size != size:
            if cs.size == 0:
                raise IndexError("%s '%s' had no values "
                                 "in common with other filegroups." %
                                 (cs.filegroup.contains, cs.name))
            log.warning("%s '%s' had %s values ignored"
                        " for consistency accross filegroups."
                        " (threshold: %s)",
                        cs.filegroup.contains, cs.name, size-cs.size, threshold)
            log.warning("Values common accross filegroup are kept instead"
                        " of throwing an exception."
                        " This is a new feature. Has not been fully tested,"
                        " especially for 'in' coordinates. Pay extra care.")

def create_data_class(dt_types, accessor=None):
    """Create a dynamic data class.

    Find a suitable name.
    Check that there is no clash between methods.

    Parameters
    ----------
    dt_type: DataBase or subclass (or a list of)
        Database classes to use, in order of
        priority for method resolution (First one in
        the list is the first class checked).

    Return
    ------
    Data class
    """
    if isinstance(dt_types, type):
        dt_types = [dt_types]

    class_name = 'Data'
    if len(dt_types) == 1:
        class_name = dt_types[0].__name__

    if isinstance(dt_types, list):
        dt_types = tuple(dt_types)

    methods = set()
    for tp in dt_types:
        for name, func in inspect.getmembers(tp, predicate=inspect.isfunction):
            if (func.__module__ != 'data_loader.data_base'
                    and name != '__init__'):
                if name in methods:
                    log.warning("%s modified by multiple DataBase "
                                "subclasses", name)
                methods.add(name)


    if accessor is None:
        d = {}
        acs_types = set()
        for tp in dt_types:
            acs_tp = type(tp.acs)
            if acs_tp != Accessor:
                if acs_tp in acs_types:
                    log.warning("Multiple subclasses of Accessor. "
                                "%s will take precedence.", dt_types[0])
                acs_types.add(acs_tp)
    else:
        d = {'acs': accessor}

    dt_class = type(class_name, dt_types, d)

    return dt_class
