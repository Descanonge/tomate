"""Construct a database easily."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import inspect
import logging
from typing import Any, Callable, Dict, Iterable, List, Sequence, Type, Union

from tomate.coordinates.coord import Coord
from tomate.coordinates.variables import Variables
from tomate.custom_types import File, KeyLike, KeyLikeValue, KeyLikeStr
from tomate.data_base import DataBase
from tomate.db_types.data_disk import DataDisk
from tomate.filegroup.filegroup_scan import make_filegroup
from tomate.filegroup.filegroup_load import FilegroupLoad
from tomate.filegroup.scanner import PostLoadingFunc, ScannerCS
from tomate.filegroup.spec import CoordScanSpec, VariableSpec
from tomate.keys.key import Key, KeyValue
from tomate.variables_info import VariablesInfo


log = logging.getLogger(__name__)


class Constructor():
    """Help creating a database object.

    :param root: Root directory of all files.
    :param coords: Coordinates. Variables can be omitted. Their order
        will dictate the coordinates order in the database and scopes.

    :attr root: str: Root directory of all files.
    :attr dims: Dict[str, Coord]: These are the 'master' coordinate that will be
        transmitted to the database object.
    :attr filegroups: List[Filegroup]: Filegroups added so far.
    :attr vi: VariablesInfo:
    :attr post_loading_funcs: List[PostLoadingFunc]: Functions applied after
        loading data, at the database level.
    :attr db_types: List[Type[DataBase]]: Subclass of DataBase to use to create
        a new dynamic database class.
    :attr allow_advanced: bool: If advanced Filegroups arrangement is allowed.
    """

    CSS = CoordScanSpec
    VS = VariableSpec

    def __init__(self, root: str, coords: List[Coord]):
        self.root = root

        if all(c.name != 'var' for c in coords):
            coords.insert(0, Variables([]))
        self.dims = {c.name: c for c in coords}

        self.vi = VariablesInfo()
        self.filegroups = []

        self.post_loading_funcs = []
        self.db_types = [DataBase]

        self.allow_advanced = False

    @property
    def current_fg(self) -> FilegroupLoad:
        """Current filegroup.

        (*ie* last filegroup added)
        """
        return self.filegroups[-1]

    def get_filegroup(self, key: Union[int, str]):
        """Get filegroup by index or name."""
        if isinstance(key, int):
            return self.filegroups[key]
        if isinstance(key, str):
            fgs = [fg for fg in self.filegroups
                   if fg.name == key]
            if len(fgs) == 0:
                raise KeyError(f"No filegroup with name {key}")
            if len(fgs) > 1:
                raise IndexError(f"More than one filegroup with name {key}")
            return fgs[0]
        raise TypeError("Key must be filegroup index or name (is {})"
                        .format(type(key)))

    def add_filegroup(self, fg_type: Type,
                      coords_fg: Iterable[CoordScanSpec],
                      name: str = '', root: str = None,
                      variables_shared: bool = False, **kwargs: Any):
        """Add filegroup.

        :param fg_type: Class of filegroup to add. Dependant on the file-format.
        :param coords_fg: Coordinates used in this grouping of files. Each
            element is an :class:`CoordScanSpec
            <tomate.filegroup.spec.CoordScanSpec>`. See its documentation
            for details.
        :param name: Name of the filegroup.
        :param root: [opt] Subfolder, relative to root.
        :param variables_shared: [opt] If the Variables dimension is shared.
            Default is False.
        :param kwargs: [opt] Passed to the `fg_type` initializator.

        Examples
        --------
        >>> cstr.add_filegroup(FilegroupNetCDF, [cstr.CSS('lat'),
        ...                                      cstr.CSS('lon'),
        ...                                      cstr.CSS('time', 'shared')]
        ...                    name='SST', root='GHRSST')
        """
        fg = make_filegroup(fg_type, self.root, self.dims,
                            coords_fg, self.vi, root, name,
                            variables_shared, **kwargs)
        self.filegroups.append(fg)

    def set_fg_regex(self, pregex: str, **replacements: str):
        """Set the pre-regex of the current filegroup.

        :param pregex: Pre-regex.
        :param replacements: [opt] Constants to replace in pre-regex.

        Examples
        --------
        >>> cstr.set_fg_regex("%(prefix)_%(time:year)",
        ...                   prefix= "SST")
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
        See :func:`DataDisk.load<tomate.db_types.data_disk.DataDisk.Load>`
        for details on `keys` arguments.

        Examples
        --------
        >>> cstr.set_coord_selection_by_value(depth=250, lat=slice(10., 30))
        """
        fg = self.current_fg
        for dim, key in keys.items():
            fg.selection[dim] = KeyValue(key)

    def set_variables_elements(self, *variables: List[VariableSpec]):
        """Set variables elements.

        This is similar to using Constructor.set_values_manually() for the
        'Variables' coordinate. For each variable, enter its information into a
        :class:`VariableSpec<tomate.filegroup.spec.VariableSpec>` object. This
        object is accessible directly from the constructor as
        `Constructor.VariableSpec` or `Constructor.VS`

        Examples
        --------
        >>> cstr.set_variables_elements(cstr.VS('SST', 'sea_surface_temp',
        ...                                     ['lat', 'lon']),
        ...                             cstr.VS('SSH', 'sea_surface_height,
        ...                                     ['lat', 'lon']))
        """
        cs = self.current_fg.cs['var']
        values = [v.name for v in variables]
        in_idx = [v.in_idx for v in variables]
        dims = [v.dims for v in variables]
        cs.set_elements_manual(values=values, in_idx=in_idx, dimensions=dims)

    def set_variables_names(self, **variables: KeyLike):
        """Only specify variables infile keys.

        Dimensions must be specified with another way (manual or constant).
        """
        cs = self.current_fg.cs['var']
        values = list(variables.keys())
        in_idx = list(variables.values())
        cs.set_elements_manual(values=values, in_idx=in_idx)

    def remove_scan_functions(*dims: str, self, kind: List[str] = None):
        """Remove scan functions.

        :param dims: Dimensions to remove scan functions from.
        :kind: [opt] Only remove specific kind.
        """
        for d in dims:
            self.current_fg.cs[d].remove_scanners(kind)

    def add_scan_in_file(self, func: Union[ScannerCS, Callable],
                         *coords: str, elements: List[str] = None,
                         restrain: List[str] = None, **kwargs: Any):
        """Set function for scanning coordinates values in file.

        :param func: Function or Scanner that captures coordinates elements.
        :param coords: Coordinates to apply this function for.
        :param elements: Elements that will be scanned with this function.
            Mandatory if '`func`' is a function, else it will redefine scanner
            elements.
        :param restrain: [opt] Only use those elements for scanning.
        :param kwargs: [opt] Keyword arguments that will be passed to the
            function.

        See also
        --------
        tomate.filegroup.scanner.ScannerCS: for details
        tomate.filegroup.scanner.coord_scan.scan_in_file_default:
            for a better description of the function interface.
        """
        fg = self.current_fg
        for name in coords:
            cs = fg.cs[name]
            cs.add_scan_function(func, kind='in', elts=elements,
                                 restrain=restrain, **kwargs)

    def add_scan_filename(self, func: Union[ScannerCS, Callable],
                          *coords: str, elements: List[str] = None,
                          restrain: List[str] = None, **kwargs: Any):
        """Set function for scanning coordinates values from filename.

        :param func: Function or Scanner that captures coordinates elements.
        :param coords: Coordinates to apply this function for.
        :param elements: Elements that will be scanned with this function.
            Mandatory if '`func`' is a function, else it will redefine scanner
            elements.
        :param restrain: [opt] Only use those elements for scanning.
        :param kwargs: [opt] Keyword arguments that will be passed to the
            function.

        See also
        --------
        tomate.filegroup.scanner.ScannerCS: for details
        tomate.filegroup.scanner.scan_filename_default:
            for a better description of the function interface.
        """
        fg = self.current_fg
        for name in coords:
            cs = fg.cs[name]
            cs.add_scan_function(func, kind='filename', elts=elements,
                                 restrain=restrain, **kwargs)

    def set_elements_constant(self, dim: str, **elements: Any):
        """Fix elements to a constant.

        :param elements: Constant to fix each element at.
            Element can be 'in_idx' or 'dimensions'.

        For all the dimension values, the specified elements
        will have the same constant value.
        """
        self.current_fg.cs[dim].set_elements_constant(**elements)

    def set_elements_manually(self, dim: str, values: List[float],
                              in_idx: List = None):
        """Set coordinate elements manually.

        All elements should have the same length as `values`.

        :param dim: Dimension to set the values for.
        :param values: Values for the coordinate.
        :param in_idx: [opt] Values of the in-file index.
            If not specified, defaults to None for all values.
        """
        if in_idx is None:
            in_idx = [None for _ in range(len(values))]

        fg = self.current_fg
        cs = fg.cs[dim]
        cs.set_scan_manual(values=values, in_idx=in_idx)

    def add_scan_coords_attributes(self, func: Callable[[File], Dict[str, Any]],
                                   *coords: str, **kwargs: Any):
        """Add a function for scanning coordinate attributes.

        Each attribute is set using CoordScan.set_attr.

        :param func: Function that recovers coordinate attribute in file.
            Returns a dictionnary {'attribute name' : value}.
        :param coords: Coordinates to apply this function for.
        :param kwargs: [opt] Passed to the function.

        See also
        --------
        tomate.filegroup.scanner.scan_coord_attributes_default:
            for a better description of the function interface.
        """
        fg = self.current_fg
        for name in coords:
            cs = fg.cs[name]
            cs.add_scan_attributes_func(func, **kwargs)

    def add_scan_general_attributes(self,
                                    func: Callable[[File], Dict[str, Any]],
                                    **kwargs: Any):
        """Add a function for scanning general data attributes.

        The attributes are added to the VI.

        :param func: Function that recovers general attributes in file. Returns
            a dictionnary {'attribute name': value}
        :param kwargs: [opt] Passed to the function.

        See also
        --------
        tomate.filegroup.filegroup.scanner.scan_attributes_default:
            for a better description of the function interface.
        """
        fg = self.current_fg
        fg.add_scan_attrs_func(func, 'gen', **kwargs)

    def add_scan_variables_attributes(self,
                                      func: Callable[[File], Dict[str, Any]],
                                      **kwargs: Any):
        """Add function for scanning variables specific attributes.

        The attributes are added to the VI.

        :param func: Function that recovers variables attributes in file. Return
             a dictionnary {'variable name': {'attribute name': value}}.
        :param kwargs: [opt] Passed to the function.

        See also
        --------
        tomate.filegroup.filegroup_scan.scan_variables_attributes_default:
            for a better description of the function interface.
        """
        fg = self.current_fg
        fg.add_scan_attrs_func(func, 'var', **kwargs)

    def set_coords_units_conversion(self, coord: str,
                                    func: Callable[[Sequence, str, str],
                                                   Sequence]):
        """Set custom function to convert coordinate values.

        Changing units use Coord.change_units_other by default.
        This method allow to override it.

        See also
        --------
        tomate.coordinates.coord.change_units_other: `func` should behave
            similarly and have the same signature.
        tomate.coordinates.time.change_units_other: For a working example.
        """
        self.current_fg.cs[coord].change_units_custom = func

    def add_post_loading_func(self, func: Callable,
                              variables: KeyLikeStr = None,
                              all_variables: bool = False,
                              current_fg: bool = False,
                              **kwargs: Any):
        """Add a post-loading function.

        Function will be called if any or all of `variables` are being loaded.
        See :class:`PostLoadingFunc<tomate.filegroup.scanner.PostLoadingFunc>`
        for details.

        :param func: Function to call. Take DataBase as first argument, and
            optional additional keywords.
        :param variables: Name of variables that should trigger the function.
            None will select all available variables.
        :param all_variables: True if all of variables must be loaded to launch
            function. False if any of the variables must be loaded (default).
        :param current_fg: Will apply only for current filegroup, otherwise will
            apply for any filegroup (default). Filegroup specific function are
            applied first.
        :param kwargs: [opt] Will be passed to the function.

        Examples
        --------
        >>> add_post_loading(func1, ['SST', 'SSH'])
        func1 will be launched if at least 'SST' and 'SSH' are loaded.
        """
        plf = PostLoadingFunc(func, variables, all_variables, **kwargs)
        if current_fg:
            for_append = self.current_fg
        else:
            for_append = self
        for_append.post_loading_funcs.append(plf)

    def set_data_types(self, db_types: Union[Type[DataBase],
                                             List[Type[DataBase]]] = None):
        """Set database subclasses.

        :param db_types: Subclass (or list of) of DataBase to derive the class
            of database from. If None, basic DataBase will be used.
            Note that :func:`make_data` will automatically `DataDisk` in
            some cases.

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

    def make_data(self, scan: bool = True,
                  create_variables: bool = True) -> DataBase:
        """Create data instance.

        Scan files, compiles coordinates values, scan variable attributes,
        create variables.

        :param scan: If the files should be scanned. Default is True.
        :param create_variables: If the variables should be created. Deactivate
            to create variables with finer control with
            :func:`DataBase.add_variable <data_base.DataBase.add_variable>`.
            Default is True.

        :returns: Data instance ready to use.
        """
        args = {'dims': list(self.dims.values()),
                'vi': self.vi}

        if scan or self.filegroups:
            if DataDisk not in self.db_types:
                self.db_types.insert(0, DataDisk)
        if DataDisk in self.db_types:
            args.update({'root': self.root,
                         'filegroups': self.filegroups})

        db_class = self.create_data_class()
        db = db_class(**args)
        db.post_loading_funcs += self.post_loading_funcs
        db.allow_advanced = self.allow_advanced

        if scan:
            db.scan_files()
            db.compile_scanned()
            db.scan_variables_attributes()
            if create_variables:
                db.create_variables(disk=True)
        return db

    def create_data_class(self) -> Type[DataBase]:
        """Create dynamic data class.

        See also
        --------
        create_data_class: for implementation
        """
        db_class = create_data_class(self.db_types)
        return db_class


def create_data_class(db_types: List[Type[DataBase]]) -> Type[DataBase]:
    """Create a dynamic data class.

    Find a suitable name. Issue a warning if there are clash between methods.

    :param db_types: DataBase subclasses to use, in order of priority for method
        resolution (First one in the list is the first class checked).
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

    db_class = type(class_name, db_types, {})
    return db_class
