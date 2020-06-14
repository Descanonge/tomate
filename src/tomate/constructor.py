"""Construct a database easily."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import logging
import os
import inspect
from typing import Any, Callable, Dict, List, Tuple, Sequence, Type, Union

from tomate.accessor import Accessor
from tomate.coordinates.coord import Coord
from tomate.coordinates.variables import Variables
from tomate.custom_types import File, KeyLike, KeyLikeValue, KeyLikeStr, KeyLikeVar
from tomate.data_base import DataBase
from tomate.db_types.data_disk import DataDisk
from tomate.filegroup.coord_scan import CoordScan
from tomate.filegroup.filegroup_load import FilegroupLoad
from tomate.keys.key import Key, KeyVar, KeyValue
from tomate.variables_info import VariablesInfo


log = logging.getLogger(__name__)


class Constructor():
    """Helps creating a database object.

    :param root: Root directory of all files.
    :param coords: Coordinates, in the order the data should be kept.
        Variables can be omitted.

    :attr root: str: Root directory of all files.
    :attr dims: Dict[str, Coord]: Coordinates, in the order
        the data should be kept.
        These are the 'master' coordinate that will be
        transmitted to the database object.
    :attr filegroups: List[Filegroup]: Filegroups added so far.
    :attr vi: VariablesInfo:

    :attr post_loading_funcs: List[Tuple[Callable[DataBase]], KeyVar,
                                   bool, Dict[str, Any]]:
        Functions applied after loading data at the database level.

    :attr db_types: List[Type[DataBase]]:
        Subclass of DataBase to use to create a new dynamic
        database class.
    :attr acs: Type[Accessor]: Subclass of Accessor
        to use for database object.

    :attr allow_advanced: bool: If advanced Filegroups arrangement is allowed.
    """

    def __init__(self, root: str, coords: List[Coord]):
        self.root = root

        if all([c.name != 'var' for c in coords]):
            coords.insert(0, Variables([]))
        self.dims = {c.name: c for c in coords}

        self.vi = VariablesInfo()
        self.filegroups = []

        self.post_loading_funcs = []
        self.db_types = [DataBase]
        self.acs = None

        self.allow_advanced = False

    @property
    def var(self) -> Variables:
        """Variables dimensions."""
        return self.dims['var']

    @property
    def coords(self) -> Dict[str, Coord]:
        """Coordinates (Dimensions without variables)."""
        out = {name: c for name, c in self.dims.items()
               if name != 'var'}
        return out

    @property
    def current_fg(self) -> FilegroupLoad:
        """Current filegroup.

        (ie last filegroup added)
        """
        return self.filegroups[-1]

    def add_filegroup(self, fg_type: Type,
                      coords_fg: List[Tuple[Union[str, Coord], Union[str, bool], str]],
                      name: str = '',
                      root: str = None,
                      variables_shared: bool = False,
                      **kwargs: Any):
        """Add filegroup.

        :param fg_type: Class of filegroup to add. Dependant on the file-format.
        :param coords_fg: Coordinates used in this grouping of files.
            Each element of the list is a tuple of length 2 or 3 with
            the coordinate (or its name), a shared flag, and eventually
            the name of the coordinate in the file.
            The flag can be 'shared' or 'in', or a boolean (True = shared).
            The name is optional, if not specified the name of the coordinate
            object is used.
            Variables dimension can be omitted.
        :param name: Name of the filegroup.
        :param root: [opt] Subfolder from root.
        :param variables_shared: [opt] If the Variables dimension is shared.
            Default is False.
        :param kwargs: [opt] Passed to the fg_type initializator.

        Examples
        --------
        >>> add_filegroup(FilegroupNetCDF, [[lat, 'in', 'latitude'],
        ...                                 [lon, 'in'],
        ...                                 [time, 'shared']])
        """
        shared_corres = {'in': False, 'shared': True}
        for i, c_fg in enumerate(coords_fg):
            if isinstance(c_fg[0], str):
                c_name = c_fg[0]
                try:
                    c_fg[0] = self.dims[c_name]
                except KeyError:
                    raise KeyError("'{}' is not in constructor dimensions.".format(c_name))
            if len(c_fg) < 3:
                c_fg.append(c_fg[0].name)
            shared = c_fg[1]
            if not isinstance(shared, bool):
                if shared not in shared_corres:
                    raise ValueError("Shared must be bool or {}\n({}, {})"
                                     .format(list(shared_corres.keys()),
                                             name, c_fg[0].name))
                shared = shared_corres[shared]
            coords_fg[i][1] = shared

        if root is None:
            root = ''
        root = os.path.join(self.root, root)

        if all([c[0].name != 'var' for c in coords_fg]):
            coords_fg.insert(0, [self.var, variables_shared, 'var'])
        fg = fg_type(root, None, coords_fg, self.vi, name, **kwargs)
        self.filegroups.append(fg)

    def set_fg_regex(self, pregex: str, **replacements: str):
        """Set the pre-regex of the current filegroup.

        :param pregex: Pre-regex.
        :param replacements: [opt] Constants to replace in pre-regex.

        Examples
        --------
        >>> cstr.set_fg_regex("%(prefix)_%(time:year)",
        ...                   {"prefix": "SST"})
        """
        if replacements is None:
            replacements = {}
        self.current_fg.set_scan_regex(pregex, **replacements)

    def set_coord_selection(self, **keys: KeyLike):
        """Set selection for CoordScan of current filegroup.

        This allows to select only a subpart of a CoordScan.
        The selection is applied by index, after scanning.

        Examples
        --------
        >>> cstr.set_coord_selection(time=[0, 1, 2], lat=slice(0, 50))
        """
        fg = self.current_fg
        for dim, key in keys.items():
            fg.selection[dim] = Key(key)

    def set_coord_selection_by_value(self, **keys: KeyLikeValue):
        """Set selection for CoordScan of current filegroup.

        This allows to select only a subpart of a CoordScan.
        The selection is applied by value, after scanning.

        :param keys: Values to select in a CoordScan.
            If is slice, use start and stop as boundaries.
            Step has no effect.
            If is float, int, or a list of, closest index
            each value is taken.

        Examples
        --------
        >>> cstr.set_coord_selection_by_value(depth=250, lat=slice(10., 30))
        """
        fg = self.current_fg
        for dim, key in keys.items():
            fg.selection[dim] = KeyValue(key)

    def set_variables_infile(self, **variables: KeyLikeVar):
        """Set variables index in the file.

        This information will be transmitted to the filegroup
        when loading.
        The argument name will be added to the variables scanning
        coordinate values, and the value to its in-file indices.

        This is similar to using Constructor.set_values_manually()
        for the 'Variables' coordinate.

        Examples
        --------
        >>> cstr.set_variables_infile(sst='SST', chl='CHL_mean')
        """
        cs = self.current_fg.cs['var']
        cs.set_scan_manual(list(variables.keys()), list(variables.values()))

    def set_scan_in_file(self, func: Callable[[CoordScan, File, List[float]],
                                              Tuple[List[float], List[int]]],
                         *coords: str,
                         only_value: bool = False, only_index: bool = False,
                         **kwargs: Any):
        """Set function for scanning coordinates values in file.

        :param func: Function that captures values and in-file indices.
        :param coords: Coordinates to apply this function for.
        :param only_value: [opt] Scan only coordinate values.
        :param only_index: [opt] Scan only in-file indices.
        :param kwargs: [opt] Keyword arguments that will be passed to the function.

        See also
        --------
        tomate.filegroup.coord_scan.scan_in_file_default:
            for a better description of the function interface.
        """
        elts = ['values', 'in_idx']
        if only_value and not only_index:
            elts.remove('in_idx')
        if only_index and not only_value:
            elts.remove('values')
        fg = self.current_fg
        for name in coords:
            cs = fg.cs[name]
            cs.set_scan_in_file_func(func, elts, **kwargs)

    def set_scan_filename(self, func: Callable[[CoordScan, List[float]],
                                               Tuple[List[float], List[int]]],
                          *coords: str,
                          only_value: bool = False, only_index: bool = False,
                          **kwargs: Any):
        """Set function for scanning coordinates values from filename.

        :param func: Function that recover values from filename.
        :param coords: Coordinates to apply this function for.
        :param only_value: [opt] Scan only coordinate values.
        :param only_index: [opt] Scan only in-file indices.
        :param kwargs: [opt] Keyword arguments that will be passed to the function.

        See also
        --------
        tomate.filegroup.coord_scan.scan_filename_default:
            for a better description of the function interface.
        """
        elts = ['values', 'in_idx']
        if only_value and not only_index:
            elts.remove('in_idx')
        if only_index and not only_value:
            elts.remove('values')
        fg = self.current_fg
        for name in coords:
            cs = fg.cs[name]
            cs.set_scan_filename_func(func, elts, **kwargs)

    def set_values_manually(self, dim: str,
                            values: List[float],
                            in_idx: List[Union[int, None]] = None):
        """Set coordinate values manually.

        Values will still be checked for consistency with
        others filegroups.

        :param dim: Dimension to set the values for.
        :param values: Values for the coordinate.
        :param in_idx: [opt] Values of the in-file index.
            If not specifile, defaults to None for all values.
        """
        if in_idx is None:
            in_idx = [None for _ in range(len(values))]

        fg = self.current_fg
        cs = fg.cs[dim]
        cs.set_scan_manual(values, in_idx)

    def set_scan_coords_attributes(self, func: Callable[[File], Dict[str, Any]],
                                   *coords: str):
        """Set a function for scanning coordinate attributes.

        The attribute is set using CoordScan.set_attr.

        :param func: Function that recovers coordinate attribute in file.
            Returns a dictionnary {'attribute name' : value}.
        :param coords: Coordinates to apply this function for.

        See also
        --------
        tomate.filegroup.coord_scan.scan_attributes_default:
            for a better description of the function interface.
        """
        fg = self.current_fg
        for name in coords:
            cs = fg.cs[name]
            cs.set_scan_attributes_func(func)

    def set_scan_general_attributes(self, func: Callable[[File], Dict[str, Any]],
                                    **kwargs: Any):
        """Set a function for scanning general data attributes.

        The attributes are added to the VI.

        :param func: Function that recovers general attributes in file.
            Returns a dictionnary {'attribute name': value}
        :param kwargs: [opt] Passed to the function.

        See also
        --------
        tomate.filegroup.filegroup_scan.scan_attributes_default:
            for a better description of the function interface.
        """
        fg = self.current_fg
        fg.set_scan_gen_attrs_func(func, **kwargs)

    def set_scan_variables_attributes(self,
                                      func: Callable[[FilegroupLoad, File, List[str]],
                                                     Dict[str, Dict[str, Any]]],
                                      **kwargs: Any):
        """Set function for scanning variables specific attributes.

        The attributes are added to the VI.

        :param func: Function that recovers variables attributes in file.
            Return a dictionnary {'variable name': {'attribute name': value}}.
        :param kwargs: [opt] Passed to the function.

        See also
        --------
        tomate.filegroup.filegroup_scan.scan_variables_attributes_default:
            for a better description of the function interface.
        """
        fg = self.current_fg
        fg.set_scan_var_attrs_func(func, **kwargs)

    def set_coords_units_conversion(self, coord: str,
                                    func: Callable[[Sequence, str, str], Sequence]):
        """Set custom function to convert coordinate values.

        Changing units use Coord.change_units_other by default.
        This method allow to override it for the current filegroup.

        See also
        --------
        tomate.coordinates.coord.change_units_other: `func` should behave similarly
            and have the same signature.
        tomate.coordinates.time.change_units_other: For a working example.
        """
        self.current_fg.cs[coord].change_units_custom = func

    def set_coord_descending(self, *coords: str):
        """Set coordinates as descending in the filegroup.

        Only useful when there is no information on the in-file
        index of each value in the files.
        """
        fg = self.current_fg
        for name in coords:
            cs = fg.cs[name]
            if cs.shared:
                log.warning("%s '%s' is shared, setting it index descending"
                            " will have no impact.", fg.variables, name)
            cs.force_idx_descending = True

    def add_post_loading_func(self, func: Callable,
                              variables: KeyLikeStr = None,
                              all_variables: bool = False,
                              current_fg: bool = False,
                              **kwargs: Any):
        """Add a post-loading function.

        Function will be called if any or all of `variables`
        are being loaded.

        :param func: Function to call. Take DataBase as first argument, and
            optional additional keywords.
        :param variables: Key for variable selection. None will select all
            available variables.
        :param all_variables: True if all of variables must be loaded to launch
            function. False if any of the variables must be loaded (default).
        :param current_fg: Will apply only for current filegroup, otherwise will apply
            for any filegroup (default).
        :param kwargs: [opt] Will be passed to the function.

        Examples
        --------
        >>> add_post_loading(func1, ['SST', 'SSH'])
        func1 will be launched if at least 'SST' and 'SSH' are loaded.
        """
        key_var = KeyVar(variables)
        if not key_var.var and key_var.type != 'none' and key_var.value != slice(None):
            raise TypeError("Variables must be specified by name (or by None).")
        if current_fg:
            for_append = self.current_fg
        else:
            for_append = self
        for_append.post_loading_funcs.append((func, KeyVar(variables),
                                              all_variables, kwargs))

    def set_data_types(self, db_types: Union[Type[DataBase], List[Type[DataBase]]] = None,
                       accessor: Type[Accessor] = None):
        """Set database and accessor subclasses.

        :param db_types: [opt] Subclass (or list of) of DataBase
            to derive the class of database from.
            If None, basic DataBase will be used.
        :param accessor: [opt] Subclass of Accessor to use for
            database.
            If None, basic Accessor will be used.

        See also
        --------
        :ref:`Additional methods` for details.
        create_data_class: for implementation
        """
        if db_types is None:
            db_types = [DataBase]
        elif not isinstance(db_types, (list, tuple)):
            db_types = [db_types]
        self.db_types = db_types
        self.acs = accessor

    def add_disk_features(self):
        """Add management of data on disk.

        If not already present.
        """
        if DataDisk not in self.db_types:
            self.db_types.insert(0, DataDisk)

    def make_data(self, scan=True) -> Type[DataBase]:
        """Create data instance.

        If scan:
        -Scan files.
        -Check coordinates for consistency across filegroups.

        :param scan: [opt] If the files should be scanned.
            Default is True.

        :returns: Data instance ready to use.
        """
        args = [list(self.dims.values()), self.vi]

        if scan or self.filegroups:
            self.add_disk_features()
        if DataDisk in self.db_types:
            args += [self.root, self.filegroups]

        db_class = self.create_data_class()
        db = db_class(*args)
        db.post_loading_funcs += self.post_loading_funcs
        db.allow_advanced = self.allow_advanced

        if scan:
            db.scan_files()
            db.compile_scanned()
            db.scan_variables_attributes()
        return db

    def create_data_class(self) -> Type[DataBase]:
        """Create dynamic data class.

        See also
        --------
        create_data_class: for implementation
        """
        db_class = create_data_class(self.db_types, self.acs)
        self.acs = db_class.acs
        return db_class


def create_data_class(db_types: List[Type[DataBase]],
                      accessor: Type[Accessor] = None) -> Type[DataBase]:
    """Create a dynamic data class.

    Find a suitable name.
    Check that there is no clash between methods.

    :param db_types: DataBase subclasses to use, in order of
        priority for method resolution (First one in
        the list is the first class checked).
    :param accessor: Accessor subclass to use for data.
        If None, the accessor found in provided data types
        will be used (according to mro priority).
    """
    if isinstance(db_types, type):
        db_types = [db_types]

    class_name = 'Data'
    if len(db_types) == 1:
        class_name = db_types[0].__name__

    if isinstance(db_types, list):
        db_types = tuple(db_types)

    methods = set()
    for tp in db_types:
        for name, func in inspect.getmembers(tp, predicate=inspect.isfunction):
            if (func.__module__ != 'tomate.data_base' and name != '__init__'):
                if name in methods:
                    log.warning("%s modified by multiple DataBase subclasses",
                                name)
                methods.add(name)

    if accessor is None:
        d = {}
        acs_types = set()
        for tp in db_types:
            acs_tp = tp.acs
            if acs_tp != Accessor:
                if acs_tp in acs_types:
                    log.warning("Multiple subclasses of Accessor. "
                                "%s will take precedence.", db_types[0])
                acs_types.add(acs_tp)
    else:
        d = {'acs': accessor}

    db_class = type(class_name, db_types, d)

    return db_class
