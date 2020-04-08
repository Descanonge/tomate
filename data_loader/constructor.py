"""Construct a database easily."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


import logging
import os
import inspect
import itertools

import numpy as np

from data_loader.variables_info import VariablesInfo
from data_loader.coordinates.variables import Variables
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
        Variables are excluded.

    Attributes
    ----------
    root: str
        Root directory of all files.
    coords: Dict[str, Coord]
        Coordinates, in the order the data should be kept.
    filegroups: List[Filegroup]
        Filegroups added so far.
    vi: VariablesInfo

    selection: List[Dict[str, Key-like]]
        Keys for selecting parts of the CoordScan.
    selection_by_value: List[Dict[str, value Key-like]]
        Keys for selecting parts of the CoordScan by value.

    allow_advanced: bool
        If advanced Filegroups arrangement is allowed.
    float_comparison: float
        Threshold for float comparison.
    """

    def __init__(self, root, coords):
        self.root = root
        self.coords = {c.name: c for c in coords}
        self.var = Variables([])
        self.vi = VariablesInfo()

        self.filegroups = []

        self.selection = []
        self.selection_by_value = []

        self.allow_advanced = False

        self.float_comparison = 1e-5

    @property
    def dims(self):
        """Dimensions (variables + coordinates)."""
        out = {'var': self.var}
        for name, c in self.coords.items():
            out[name] = c
        return out

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
            Name of the variable.
        attributes: optional
            Variable specific information.

        Examples
        --------
        >>> name = "SST"
        ... attrs = {'fullname': 'Sea Surface Temperature',
        ...          'max_value': 40.}
        ... cstr.add_variable(name, **attrs)
        """
        self.var.append(variable)
        self.vi.add_variable(variable, **attributes)

    def add_infos(self, **infos):
        """Add information to the vi.

        Add not variable-specific attributes to the vi.

        Parameters
        ----------
        infos: Any

        Examples
        --------
        >>> cstr.add_infos(altimetry_data=['SSH', 'U', 'V'])
        """
        self.vi.add_infos(**infos)

    def add_filegroup(self, fg_type, contains, coords, root=None,
                      variables_shared=False, **kwargs):
        """Add filegroup.

        Parameters
        ----------
        fg_type: FilegroupLoad subclass
            Class of filegroup to add. Dependant on the file-format.
        contains: List[str], str
            List of variables contained in this grouping
            of files.
            Superseded by 'var' in `coords` if present.
        coords: List[Coord, shared: str or bool]
            Coordinates used in this grouping of files.
            Each element of the list is a length 2 tuple of
            the coordinate name, and a shared flag.
            The flag can be 'shared' or 'in'.
            Variables dimension can be omitted.
        root: str, optional
            Subfolder from root.
        variables_shared: bool, optional
            If the Variables dimension is shared.
            Default is False.
        kwargs: Any, optional
            Passed to the fg_type initializator.

        Examples
        --------
        >>> add_filegroup(FilegroupNetCDF, ['Chla', 'Chla_error'],
        ...               [['lat', 'in'], ['lon', 'in'], ['time', 'shared']])
        """
        for c_fg in coords:
            if len(c_fg) < 3:
                c_fg.append(c_fg[0].name)
        shared_corres = {'in': False, 'shared': True}
        for i, [c, shared, _] in enumerate(coords):
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

        coords.insert(0, [self.var, variables_shared, 'var'])
        fg = fg_type(root, contains, None, coords, self.vi,
                     variables_shared=variables_shared, **kwargs)
        self.filegroups.append(fg)

        self.selection.append({})
        self.selection_by_value.append({})

    def set_fg_regex(self, pregex, replacements=None):
        """Set the pre-regex of the current filegroup.

        Parameters
        ----------
        pregex: str
            Pre-regex.
        replacements: Dict[str, str], optional
            Constants to replace in pre-regex.

        Examples
        --------
        >>> cstr.set_fg_regex("%(prefix)_%(time:year)",
        ...                   {"prefix": "SST"})
        """
        if replacements is None:
            replacements = {}
        self.current_fg.set_scan_regex(pregex, **replacements)

    def set_coord_selection(self, **keys):
        """Set selection for CoordScan of current filegroup.

        This allows to select only a subpart of a CoordScan.
        The selection is applied by index, after scanning.

        Parameters
        ----------
        keys: Key-like

        Examples
        --------
        >>> cstr.set_coord_selection(time=[0, 1, 2], lat=slice(0, 50))
        """
        for dim, key in keys.items():
            self.selection_by_value[-1].pop(dim, None)
            self.selection[-1][dim] = key

    def set_coord_selection_by_value(self, **keys):
        """Set selection for CoordScan of current filegroup.

        This allows to select only a subpart of a CoordScan.
        The selection is applied by value, after scanning.

        Parameters
        ----------
        keys: int, float, slice
            Values to select in a CoordScan.
            If is slice, use start and stop as boundaries.
            Step has no effect.
            If is float, int, or a list of, closest index
            each value is taken.

        Examples
        --------
        >>> cstr.set_coord_selection_by_value(depth=250, lat=slice(10., 30))
        """
        for dim, key in keys.items():
            self.selection[-1].pop(dim, None)
            self.selection_by_value[-1][dim] = key

    def set_variables_infile(self, *variables, **kw_variables):
        """Set variables index in the file.

        This information will be transmitted to the filegroup
        when loading.
        It can be a integer or a string
        under which the variable is found in file.

        Variables not specified will be attributed the default
        value (in-file index identical to the variable name).

        This is similar to using Constructor.set_scan_manual()
        for the 'Variables' coordinate.

        Parameters
        ----------
        variables: int, str, None, optional
            Argument in the order of variables indicated
            when adding the last filegroup.
        kw_variables: int, str, None, optional
            Argument name is the variable name.
            Takes precedence over `variables` argument.

        Examples
        --------
        >>> cstr.set_variables_infile('SST', 'CHL')

        >>> cstr.set_variables_infile(sst='SST')
        """
        fg = self.current_fg
        for i, inf in enumerate(variables):
            var = fg.variables[i]
            if var not in kw_variables:
                kw_variables[var] = inf

        cs = fg.cs['var']
        values = fg.variables[:]
        in_idx = [kw_variables.get(var, None) for var in values]
        cs.set_scan_manual(values, in_idx)

    def set_scan_in_file(self, func, *coords, **kwargs):
        """Set function for scanning coordinates values in file.

        Parameters
        ----------
        func: Callable[[CoordScan, file, values: List[float]],
                       [values: List[float], in_idx: List[int]]]
            Function that captures values and in-file index
        coords: str
            Coordinates to apply this function for.
        kwargs: Any, optional
            Keyword arguments that will be passed to the function.

        Notes
        -----
        See coord_scan.scan_in_file_default() for a better description of
        the function interface.
        """
        fg = self.current_fg
        for name in coords:
            cs = fg.cs[name]
            cs.set_scan_in_file_func(func, **kwargs)

    def set_scan_filename(self, func, *coords, **kwargs):
        """Set function for scanning coordinates values from filename.

        Parameters
        ----------
        func: Callable[[CoordScan, values: List[Float]],
                       [values: List[float], in_idx: List[int]]
            Function that recover values from filename.
        coords: str
            Coordinates to apply this function for.
        kwargs: Any, optional
            Keyword arguments that will be passed to the function.

        Notes
        -----
        See coord_scan.scan_filename_default() for a better description of
        the function interface.
        """
        fg = self.current_fg
        for name in coords:
            cs = fg.cs[name]
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
        in_idx: List[int/None], optional
            Values of the in-file index.
            If not specifile, defaults to None for all values.
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
                       [Dict[info name: str, Any]]]

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
        coords: str
        """
        fg = self.current_fg
        for name in coords:
            cs = fg.cs[name]
            if cs.shared:
                log.warning("%s '%s' is shared, setting it index descending"
                            " will have no impact.", fg.variables, name)
            cs.force_idx_descending = True

    def scan_files(self):
        """Scan files.

        Scan files.
        Apply selection of CS.
        Find total availables coordinates values
        accross filegroups.
        Find what values are contained within each fg.
        If allowed is not allowed, select only common
        values accross filegroups.
        Check if data points are duplicates accross filegroups.
        """
        self.check_regex()
        for fg in self.filegroups:
            fg.scan_files()

        self._apply_coord_selections()

        values = self._get_coord_values()
        self._find_contained(values)
        if not self.allow_advanced:
            self._get_intersection(values)
            self._apply_coord_values(values)
            self._find_contained(values)
        else:
            self._apply_coord_values(values)
        self.check_duplicates()

    def _apply_coord_selections(self):
        """Apply selection on CoordScan.

        Only treat a subpart of a coordinate.
        Selection set by user.
        Non-selected parts are forgotten.
        """
        for i, fg in enumerate(self.filegroups):
            for dim, key in self.selection[i].items():
                fg.cs[dim].slice(key)
            for dim, key in self.selection_by_value[i].items():
                cs = fg.cs[dim]
                if isinstance(key, slice):
                    idx = cs.subset(slice.start, slice.stop)
                else:
                    idx = cs.get_indices(key)
                cs.slice(idx)

    def _get_coord_values(self):
        """Aggregate all available coordinate values.

        Returns
        -------
        Dict[str, Array]
            Values for each dimension.
        """
        values_c = {}
        for c in self.dims:
            values = []
            for fg in self.filegroups:
                if fg.cs[c].size is not None:
                    values += list(fg.cs[c][:])

            values = np.array(values)
            if c != 'var':
                values.sort()
                duplicates = np.abs(np.diff(values)) < self.float_comparison
                values = np.delete(values, np.where(duplicates))

            values_c[c] = values
        return values_c


    def _apply_coord_values(self, values):
        """Set found values to master coordinates.

        Parameters
        ----------
        values: Dict[str, Array]
        """
        for dim, val in values.items():
            self.dims[dim].update_values(val)

    def _get_contained(self, dim, inner, outer):
        """Find values of inner contained in outer.

        Parameters
        ----------
        dim: str
        inner: Array[Any]
            Smaller list of values.
            Can be floats, in which case self.float_comparison
            is used as a threshold comparison.
            Can be strings, if `dim` is 'var'.
        outer: Array[Any]
            Longer list of values.

        Returns
        -------
        contains: List
            List of the index of the outer values in the
            inner list. If the value is not contained in
            inner, the index is `None`.
        """
        contains = []

        # TODO: comparison taken in charge by coordinate
        for value in outer:
            if dim == 'var':
                idx = np.where(inner == value)[0]
            else:
                idx = np.where(np.abs(inner-value) < self.float_comparison)[0]
            if len(idx) == 0:
                idx = None
            else:
                idx = idx[0]
            contains.append(idx)
        return contains

    def _find_contained(self, values):
        """Find what values are contained in each fg.

        Set the `contains` values for all filegroups,
        according to all available values.

        Parameters
        ----------
        values: Dict[str, Array]
            All available values for each coordinate.
        """
        for fg in self.filegroups:
            for dim, cs in fg.cs.items():
                # No information on CS values:
                # no conversion between avail and FG
                if cs.size is None:
                    contains = np.arange(len(values[dim]))
                else:
                    contains = self._get_contained(dim, cs[:], values[dim])
                    contains = np.array(contains)
                fg.contains[dim] = contains

    def _get_intersection(self, values):
        """Get intersection of coordinate values.

        Only keep coordinates values common to all filegroups.
        The variables dimensions is excluded from this.
        Slice CoordScan and `contains` accordingly.

        Parameters
        ----------
        values: Dict[str, Array]
            All values available for each dimension.
            Modified in place to only values common
            accross filegroups.
        """
        for dim in self.coords:
            any_cut = False
            for fg in self.filegroups:
                none = np.equal(fg.contains[dim], None)
                rem = np.where(none)[0]
                sel = np.where(~none)[0]
                if rem.size > 0:
                    any_cut = True
                    self._slice_cs(dim, values, rem, sel)

            if any_cut:
                c = self.filegroups[0].cs[dim]
                log.warning("Common values taken for '%s', %d values ranging %s",
                            dim, c.size, c.get_extent_str())

    def _slice_cs(self, dim, values, remove, select):
        """Slice all CoordScan according to smaller values.

        Parameters
        ----------
        dim: str
            Dimension to slice.
        values: Array
            New values.
        remove: Array[int]
            Indices to remove from available.
        select: Array[int]
            Indices to keep in available.

        Raises
        ------
        IndexError
            If no common values are found.
        """
        values[dim] = np.delete(values[dim], remove)
        for fg_ in self.filegroups:
            cs = fg_.cs[dim]
            if cs.size is not None:
                indices = fg_.contains[dim][select]
                indices = np.delete(indices,
                                    np.where(np.equal(indices, None))[0])
                if indices.size == 0:
                    raise IndexError("No common values for '%s'." % dim)

                if indices.size != cs.size:
                    log.warning("'%s' in %s will be cut: found %d values ranging %s",
                                dim, fg_.variables, fg_.cs[dim].size,
                                fg_.cs[dim].get_extent_str())
                cs.slice(indices.astype(int))
            fg_.contains[dim] = np.delete(fg_.contains[dim], remove)

    def check_duplicates(self):
        """Check for duplicate data points.

        ie if a same data point (according to coordinate values)
        can be found in two filegroups.

        Raises
        ------
        ValueError:
            If there is a duplicate.
        """
        for fg1, fg2 in itertools.combinations(self.filegroups, 2):
            intersect = []
            for c1, c2 in zip(fg1.contains.values(), fg2.contains.values()):
                w1 = np.where(~np.equal(c1, None))[0]
                w2 = np.where(~np.equal(c2, None))[0]
                intersect.append(np.intersect1d(w1, w2).size)
            if all(s > 0 for s in intersect):
                raise ValueError("Duplicate values in filegroups %s and %s"
                                 % (fg1.variables, fg2.variables))

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
                            fg.variables, coords)
                raise RuntimeError(mess)

    def make_data(self, dt_types, accessor=None, scan=True):
        """Create data instance.

        Check a regex is present in every filegroup.
        Scan files.
        Check coordinates for consistency across filegroups.
        Create database object from multiple subclasses of data.

        Parameters
        ----------
        dt_type: Type, List[Type]
            DataBase subclasses to use, in order of
            priority for method resolution (Methods and
            attributes of the first one in
            the list take precedence).
        accessor: Type, optional
            Subclass of Accessor.
            If None, the accessor from the provided data
            types is used.
        scan: bool, optional
            If the files should be scanned.
            Default is True.

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
            if not self.filegroups:
                raise RuntimeError("No filegroups in constructor.")
            self.scan_files()

        dt_class = create_data_class(dt_types, accessor)

        # variables = list(self.vi.var)
        # for fg in self.filegroups:
        #     variables += fg.variables
        # for var in variables:
        #     if var not in self.vi:
        #         self.vi.add_variable(var)

        dt = dt_class(self.root, self.filegroups, self.vi, *self.dims.values())
        return dt



def create_data_class(dt_types, accessor=None):
    """Create a dynamic data class.

    Find a suitable name.
    Check that there is no clash between methods.

    Parameters
    ----------
    dt_type: Type, List[type]
        DataBase subclasses to use, in order of
        priority for method resolution (First one in
        the list is the first class checked).
    accessor: Type, optional
        Accessor subclass to use for data.
        If None, the accessor found in provided data types
        will be used (according to mro priority).

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
            acs_tp = tp.acs
            if acs_tp != Accessor:
                if acs_tp in acs_types:
                    log.warning("Multiple subclasses of Accessor. "
                                "%s will take precedence.", dt_types[0])
                acs_types.add(acs_tp)
    else:
        d = {'acs': accessor}

    dt_class = type(class_name, dt_types, d)

    return dt_class
