"""Base class for data."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


import logging
from typing import Dict, List

import numpy as np

from data_loader.key import Keyring
from data_loader.accessor import Accessor
from data_loader.scope import Scope


log = logging.getLogger(__name__)


class DataBase():
    """Encapsulate data array and info about the variables.

    The data itself is stored in the data attribute.
    It can be loaded from disk using multiple `Filegroups`.
    The data can be conveniently accessed using the `view` method.

    The data varies along coordinates (akin to dimensions).
    An ensemble of coordinates and variables constitutes a `Scope`
    This object has three different scopes:
    \*avail: all data available on disk
    \*loaded: part of that data that is loaded in memory
    \*select: part of data selected

    Coordinates objects, the list of variables, and the shape
    of data, attributes of the different scopes objects, are
    directly accessible from the data object.
    If data has been loaded, the 'loaded' scope is used,
    otherwise the 'available' scope is used.

    Data and coordinates can be accessed as items:
    `Data[{name of variable | name of coordinate}]`.
    Coordinates can be accessed as attributes:
    `Data.name_of_coordinate`.

    See :doc:`../data` for more information.

    Parameters
    ----------
    root: str
        Root data directory containing all files.
    filegroups: List[Filegroups]
    vi: VariablesInfo
        Information on the variables and data.
    coords: Coord
        Coordinates.

    Attributes
    ----------
    data: Numpy array
        Data array if loaded.
    filegroups: List[Filegroup]
    _fg_idx: Dict[variable: str, int]
        Index of filegroup for each variable

    vi: VariablesInfo
        Information on the variables and data.

    coords_name: List[str]
        Coordinates names, in the order the data
        is kept in the array.

    avail: Scope
        Scope of available data (on disk)
    loaded: Scope
        Scope of loaded data
    select: Scope
        Scope of selected data.

    acs: Accessor (or subclass)
        Object to use to access the data.

    do_post_load: Callable
        Function applied after loading data.
    """

    acs = Accessor()

    def __init__(self, root, filegroups, vi, *coords):
        self.root = root

        names = [c.name for c in coords]
        self.coords_name = names

        self.avail = Scope(vi.var, coords)
        self.loaded = self.avail.copy()
        self.select = self.avail.copy()
        self.loaded.empty()
        self.select.empty()
        self.avail.name = 'available'
        self.loaded.name = 'loaded'
        self.select.name = 'selected'

        self._fg_idx = {}
        self.filegroups = filegroups
        for i, fg in enumerate(filegroups):
            for var in fg.contains:
                self._fg_idx.update({var: i})

        self.vi = vi

        self.data = None

        self.link_filegroups()

        self.do_post_load = do_post_load_default

    def __str__(self):
        s = ["Data object"]

        s1 = "Class: %s, Bases: " % self.__class__.__name__
        s2 = ', '.join(self.bases.values())
        s.append(s1 + s2)
        s.append('')

        s.append("Data available: \n%s" % str(self.avail))
        s.append('')

        if self.data is None:
            s.append('Data not loaded')
        else:
            s.append('Data loaded: \n%s' % str(self.loaded))
        s.append('')

        if self.select.is_empty():
            s.append('No data selected')
        else:
            s.append('Data selected: \n%s' % str(self.select))
        s.append('')

        s.append("%d Filegroups:" % len(self.filegroups))
        s += ['\t%s' % ', '.join(fg.contains) for fg in self.filegroups]

        return '\n'.join(s)

    def __repr__(self):
        return '\n'.join([super().__repr__(), str(self)])

    @property
    def bases(self) -> Dict[str, str]:
        """Bases classes.

        Returns dictionary of bases name and their fullname
        (with module).

        Returns
        -------
        {class name: full name with module}
        """
        bases = self.__class__.__bases__
        out = {c.__name__: '%s.%s' % (c.__module__, c.__name__)
               for c in bases}
        return out

    def _check_loaded(self):
        """Check if data is loaded.

        Raises
        ------
        RuntimeError
            If the data is not loaded.
        """
        if self.data is None:
            raise RuntimeError("Data not loaded.")

    def __getitem__(self, y: str):
        """Return a coordinate, or data for a variable.

        If y is a coordinate name, return the coordinate of current scope.
        If y is a variable name, return the corresponding data slice.

        Parameters
        ----------
        y: str
            Coordinate or variable name.

        Raises
        ------
        KeyError
            If key is not a coordinate or variable.
        """
        if isinstance(y, str):
            if y in self.loaded.var:
                y = self.idx[y]
                return self.data[y]
            if y in self.coords_name:
                return self.scope[y]
        raise KeyError("Key '%s' not in coordinates or variables" % y)

    def __getattribute__(self, item):
        """Get attribute.

        If item is a coordinate name, return coordinate from
        current scope.
        If item is 'var', return list of variable from
        current scope.
        """
        if item in super().__getattribute__('coords_name') + ['var']:
            if not self.loaded.is_empty():
                scope = super().__getattribute__('loaded')
            else:
                scope = super().__getattribute__('avail')
            return scope[item]
        return super().__getattribute__(item)

    @property
    def scope(self) -> Scope:
        """Loaded scope if not empty, available scope otherwise."""
        if not self.loaded.is_empty():
            return self.loaded
        return self.avail

    def get_scope(self, scope) -> Scope:
        """Get scope by name."""
        if isinstance(scope, str):
            scope = {'avail': self.avail,
                     'loaded': self.loaded,
                     'select': self.select}[scope]
        return scope

    @property
    def idx(self) -> Dict[str, int]:
        """Index of each variable in the data array.

        {variable name: index}
        """
        return self.loaded.idx

    def view(self, variables=None, keyring=None, **keys):
        """Returns a subset of loaded data.

        Keys act on loaded scope.
        If a key is an integer (or variables is a single string),
        the corresponding dimension in the array will be squeezed.

        Parameters
        ----------
        variables: str or List[str], optional
            If None, all variables are taken.
        keyring: Keyring, optional
            Keyring specifying parts of coordinates to take.
        keys: Key-like, optional
            Parts of coordinates to take.
            Take precedence over keyring.

        Returns
        -------
        Array
            Subset of data, in storage order.
        """
        self._check_loaded()

        if keyring is None:
            keyring = Keyring()
        else:
            keyring = keyring.copy()

        keyring.update(keys)
        keyring.make_full(self.coords_name)
        keyring['var'] = self.idx[variables]
        keyring.make_total()
        keyring.sort_by(['var'] + self.coords_name)
        return self.acs.take(keyring, self.data)

    def view_selected(self, variables=None, keyring=None, **keys):
        """Returns a subset of loaded data.

        Subset is specified by a scope.
        The selection scope is expected to be created from
        the loaded one.

        Parameters
        ----------

        Returns
        -------
        Array
        """
        scope = self.select
        if scope.is_empty():
            raise Exception("Selection scope is empty ('%s')." % scope.name)
        if scope.parent_scope != self.loaded:
            raise Exception("The parent scope is not the loaded data scope."
                            " (is '%s')" % scope.parent_scope.name)

        scope_ = scope.copy()
        scope_.slice(variables, keyring, int2list=False, **keys)
        return self.view(scope_.var, scope_.parent_keyring)

    def view_scope(self, scope):
        """Returns a subset of loaded data.

        Subset is specified by common range of coordinates
        of scope parameter, and loaded scope.

        Parameters
        ----------
        scope: Scope

        Returns
        -------
        Array
        """
        log.warning("Not functionnal.")
        if scope.is_empty():
            raise RuntimeError("Scope is empty.")

        variables = scope.var
        keyring = Keyring()
        for name, c in scope.coords.items():
            key = self.loaded[name].subset(*c.get_limits())
            keyring[name] = key
        return self.view(variables, keyring)

    def view_ordered(self, order, variables=None, keyring=None, **keys):
        """Returns a reordered subset of data.

        The ranks of the array are rearranged to follow
        the specified coordinates order.
        Keys act on loaded scope.

        Parameters
        ----------
        order: List[str]
            List of coordinates names in required order.
            The 'var' keyword can also be used to rearrange
            the variable rank.
            Not all coordinates need to be specified, but
            all coordinates specified must be in the subset
            dimensions.
        variables: str or List[str], optional
        keyring: Keyring, optional
        keys: Key-like, optional

        Examples
        --------
        >>> print(dt.coords_name)
        ['time', 'lat', 'lon']
        >>> print(dt.shape)
        [12, 300, 500]
        >>> a = dt.view_orderd(['lon', 'lat'], time=[1])
        ... print(a.shape)
        [1, 500, 300]

        See also
        --------
        Accessor.reorder: The underlying function.
        numpy.moveaxis: The function used in default Accessor.
        view: For details on subsetting data (without reordering).
        """
        self._check_loaded()

        if keyring is None:
            keyring = Keyring()
        else:
            keyring = keyring.copy()

        keyring.update(keys)
        keyring.make_full(self.coords_name)
        keyring['var'] = self.idx[variables]
        keyring.make_total()
        keyring.sort_by(['var'] + self.coords_name)

        array = self.acs.take(keyring, self.data)
        return self.acs.reorder(keyring, array, order)

    def iter_slices(self, coord, size=12):
        """Iter through slices of a coordinate.

        Scope will be loaded if not empty, available otherwise.
        The prescribed slice size is a maximum, the last
        slice can be smaller.

        Parameters
        ----------
        coord: str
            Coordinate to iterate along to.
        size: int, optional
            Size of the slices to take.

        Returns
        -------
        List[slice]
        """
        return self.scope.iter_slices(coord, size)

    def iter_slices_month(self, coord='time'):
        """Iter through monthes of a time coordinate.

        Parameters
        ----------
        coord: str, optional
            Coordinate to iterate along to.
            Must be subclass of Time.

        Returns
        -------
        List[List[int]]

        See also
        --------
        iter_slices: Iter through any coordinate
        """
        return self.scope.iter_slices_month(coord)

    def link_filegroups(self):
        """Link filegroups and data."""
        for fg in self.filegroups:
            fg.db = self
            fg.acs = self.acs

    @property
    def ndim(self) -> int:
        """Number of dimensions."""
        return len(self.coords_name) + 1

    @property
    def n_coords(self) -> int:
        """Number of coordinates."""
        return len(self.coords_name)

    @property
    def shape(self) -> List[int]:
        """Shape of the data from current scope.

        Scope is loaded if not empty, available otherwise.
        """
        return self.scope.shape

    def get_coord_name(self, name: str) -> str:
        """Return coord name.

        Search within alternative names.

        Parameters
        ----------
        name: str
            Coordinate name or alternative name.

        Returns
        -------
        str
            Coordinate name.

        Raises
        ------
        KeyError
            If the name is not found.
        """
        # First check name
        for c_name in self.avail:
            if c_name == name:
                return c_name

        # Then check name_alt
        for c_name, coord in self.avail.coords.items():
            if name in coord.name_alt:
                return c_name

        raise KeyError("%s not found" % name)

    def get_limits(self, *coords, scope=None, keyring=None, **keys):
        """Return limits of coordinates.

        Min and max values for specified coordinates.
        Scope is loaded if not empty, available otherwise.

        Parameters
        ----------
        coords: str
            Coordinates name.
            If None, defaults to all coordinates, in the order
            of data.
        keyring: Keyring, optional
            Subset coordinates.
        keys: Key-like, optional
            Subset coordinates.
            Take precedence over keyring.

        Returns
        -------
        limits: List[float]
            Min and max of each coordinate. Flattened.

        Examples
        --------
        >>> print(dt.get_limits('lon', 'lat'))
        [-20.0 55.0 10.0 60.0]

        >>> print(dt.get_extent(lon=slice(0, 10)))
        [-20.0 0.]
        """
        scope = self.get_scope(scope)
        if scope is None:
            scope = self.scope
        return scope.get_limits(*coords, keyring=keyring, **keys)

    def get_extent(self, *coords, scope=None, keyring=None, **keys):
        """Return extent of loaded coordinates.

        Return first and last value of specified coordinates.

        Parameters
        ----------
        coords: str
            Coordinates name.
            If None, defaults to all coordinates, in the order
            of data.
        keyring: Keyring, optional
            Subset coordinates.
        keys: Key-like, optional
            Subset coordinates.
            Take precedence over keyring.

        Returns
        -------
        extent: List[float]
            First and last values of each coordinate.

        Examples
        --------
        >>> print(dt.get_extent('lon', 'lat'))
        [-20.0 55.0 60.0 10.0]

        >>> print(dt.get_extent(lon=slice(0, 10)))
        [-20.0 0.]
        """
        scope = self.get_scope(scope)
        if scope is None:
            scope = self.scope
        return scope.get_extent(*coords, keyring=keyring, **keys)

    def get_kw_keys(self, *keys, **kw_keys):
        """Make keyword keys when asking for coordinates parts.

        From a mix of positional and keyword argument,
        make a list of keywords.
        Keywords arguments take precedence over positional arguments.
        Positional argument shall be ordered as the coordinates
        are ordered in data.

        Parameters
        ----------
        keys: Key-like, optional
        kw_keys: Key-like, optional

        Exemples
        --------
        >>> print( dt.get_kw_keys([0, 1], lat=slice(0, 10)) )
        {'time': [0, 1], 'lat': slice(0, 10)}
        """
        for i, key in enumerate(keys):
            name = self.coords_name[i]
            if name not in kw_keys:
                kw_keys[name] = key
        return kw_keys

    def get_subscope(self, scope='avail', variables=None, keyring=None,
                     int2list=True, **keys):
        """Return subset of scope.

        Parameters
        ----------
        variables: str, List[str], optional
        keyring: Keyring, optional
        scope: str, Scope, optional
            Scope to subset.
            If str, can be {'avail', 'loaded', 'select'},
            corresponding scope of data will then be taken.
        keys: Key-like, optional

        Returns
        -------
        Scope
            Copy of input scope, sliced with specified keys.
        """
        scope = self.get_scope(scope)
        subscope = scope.copy()
        subscope.slice(variables, keyring, int2list=int2list, **keys)
        subscope.parent_scope = scope
        return subscope

    def select_from_scope(self, scope='avail', variables=None, keyring=None, **keys):
        """Set selected scope from another scope.

        Wrapper around :func:`get_subscope`.

        Parameters
        ----------
        scope: str, Scope, optional
            Scope to subset.
            If str, can be {'avail', 'loaded', 'select'},
            corresponding scope of data will then be taken.
        variables: str, List[str], optional
        keyring: Keyring, optional
        keys: Key-like, optional

        See also
        --------
        get_subscope
        """
        self.select = self.get_subscope(scope, variables, keyring,
                                        int2list=False, **keys)
        self.select.name = 'select'

    def select_from_avail(self, variables=None, keyring=None, **keys):
        """Set selected scope from available.

        Wrapper around select_from_scope().
        """
        self.select_from_scope(scope='avail', variables=variables, keyring=keyring, **keys)

    def select_from_loaded(self, variables=None, keyring=None, **keys):
        """Set selected scope from loaded.

        Wrapper around select_from_scope().
        """
        self.select_from_scope(scope='loaded', variables=variables, keyring=keyring, **keys)

    def slice_data(self, variables=None, keyring=None, **keys):
        """Slice loaded data.

        Keys act on loaded scope.

        Parameters
        ----------
        variables: str or List[str], optional
            Variables to select, from those already loaded.
            If None, no change are made.
        keyring: Keyring, optional
        keys: Key-like, optional
        """
        self._check_loaded()
        self.loaded = self.get_subscope(variables, keyring, 'loaded', **keys)
        self.data = self.view(variables, keyring, **keys)

    def unload_data(self):
        """Remove data, return coordinates and variables to all available."""
        self.data = None
        self.loaded = self.avail.copy()
        self.loaded.name = 'loaded'

    def load_data_value(self, variables=None, **keys):
        """Load part of data from disk into memory.

        Part of the data to load is specified by values.

        .. deprecated:: 0.3.1
            Is replaced by DataBase.load_by_value().
            Will be removed in 0.4.
        """
        log.warning("load_data_value() is replaced by load_by_value()"
                    " and will be removed in 0.4.")
        self.load_by_value(variables=variables, **keys)

    def load_by_value(self, variables=None, **keys):
        """Load part of data from disk into memory.

        Part of the data to load is specified by values.

        Parameters
        ----------
        variables: str or List[str], optional
            Variables to load.
        keys: list[float], float, int, slice, optional
            Values to select for a coordinate.
            If is slice, use start and stop as boundaries. Step has no effect.
            If is float, int, or a list of, closest index for each value is taken.

        Examples
        --------
        Load latitudes from 10N to 30N.
        >>> dt.load_by_value('SST', lat=slice(10, 30))

        Load latitudes from 5N to maximum available.
        >>> dt.load_by_value('SST', lat=slice(5, None))

        Load depth closest to 500.
        >>> dt.load_by_value(None, depth=500.)

        Load depths closest to 0, 10, 50
        >>> dt.load_by_value(None, depth=[0, 10, 50])
        """
        keys_ = {}
        for name, c in self.avail.coords.items():
            key = keys.get(name)
            if key is None:
                key = slice(None, None)
            elif isinstance(key, slice):
                key = c.subset(key.start, key.stop)
            elif isinstance(key, (list, tuple, np.ndarray)):
                key = [c.get_index(k) for k in key]
            else:
                key = c.get_index(key)
            keys_[name] = key
        self.load(variables, **keys_)

    def load_data(self, variables, *keys, **kw_keys):
        """Load part of data from disk into memory.

        .. deprecated:: 0.3.1
            Is replaced by DataBase.load().
            Will be removed in 0.4.
        """
        log.warning("load_data() is replaced by load()"
                    " and will be removed in 0.4.")
        self.load(variables, *keys, **kw_keys)

    def load(self, variables, *keys, **kw_keys):
        """Load part of data from disk into memory.

        What variables, and what part of the data
        corresponding to coordinates indices can be specified.
        Keys specified to subset data act on the available scope.
        If a parameter is None, all available is taken for that
        parameter.

        Parameters
        ----------
        variables: str or List[str]
            Variables to load.
        keys: int, slice, List[int], optional
            What subset of coordinate to load. The order is that
            of self.coords.
        # TODO: force: Does not simplify those coords keys
        kw_keys: int, slice, or List[int], optional
            What subset of coordinate to load. Takes precedence
            over positional `coords`.

        Examples
        --------
        Load everything available

        >>> dt.load(None)

        Load first index of the first coordinate for the SST variable

        >>> dt.load("SST", 0)

        Load everything for SST and Chla variables.

        >>> dt.load(["SST", "Chla"], slice(None, None), None)

        Load time steps 0, 10, and 12 of all variables.

        >>> dt.load(None, time=[0, 10, 12])

        Load first index of the first coordinate, and a slice of lat
        for the SST variable.

        >>> dt.load("SST", 0, lat=slice(200, 400))
        """
        self.unload_data()

        kw_keys = self.get_kw_keys(*keys, **kw_keys)
        keyring = Keyring(**kw_keys)
        keyring.make_full(self.coords_name)
        keyring.make_total()
        keyring.make_int_list()
        self.loaded = self.get_subscope('avail', variables, keyring)
        self.loaded.name = 'loaded'

        self.data = self.allocate(self.shape)

        fg_var = self._get_filegroups_for_variables(self.loaded.var)
        for fg, var_load in fg_var:
            fg.load_data(var_load, keyring)

        try:
            self.do_post_load(self)
        except NotImplementedError:
            pass

    def load_selected(self, scope=None):
        """Load data from a child scope of available.

        Subset is specified by a scope.
        The selection scope is expected to be created from
        the available one.

        Parameters
        ----------
        scope: Scope
            Selected scope created from available scope.
            Defaults to `self.select`.
        """
        if scope is None:
            scope = self.select
        if scope.is_empty():
            raise Exception("Selection scope is empty ('%s')." % scope.name)
        if scope.parent_scope != self.avail:
            raise Exception("The parent scope is not the available data scope."
                            " (is '%s')" % scope.parent_scope.name)

        self.load(scope.var, **scope.parent_keyring.kw)

    def allocate(self, shape):
        """Allocate data array.

        Parameters
        ----------
        shape: List[int]
            Shape of the array to allocate.

        Returns
        -------
        Array
        """
        log.info("Allocating numpy array of shape %s", shape)
        return self.acs.allocate(shape)

    def _get_filegroups_for_variables(self, variables):
        """Find the filegroups corresponding to variables.

        Parameters
        ----------
        variables: List[str]

        Returns
        -------
        fg_var: List[List[Filegroup, List[str]]
            A list of the filegroups with the corresponding variables.
        """

        # find the filegroups we need to load
        fg_var = []
        for var in variables:
            fg = self.filegroups[self._fg_idx[var]]
            try:
                idx = [z[0] for z in fg_var].index(fg)
            except ValueError:
                fg_var.append([fg, []])
                idx = -1
            fg_var[idx][1].append(var)

        return fg_var

    def set_post_load_func(self, func):
        """Set function for post loading treatements.

        Parameters
        ----------
        func: Callable[[DataBase or subclass]]
            Function to execute after data is loaded.
            See do_post_load() for a better description
            of the function interface.

        """
        self.do_post_load = func

    def set_data(self, var, data):
        """Set the data for a single variable.

        Parameters
        ----------
        var: str
            Variable to set the data to.
        data: Array
            Array of the correct shape for currently
            selected coordinates. Has no axis for variables.

        Raises
        ------
        IndexError
            If the data has not the right dimension.
        ValueError
            If the data is not of the shape of current selection.
        """
        if self.acs.ndim(data) != self.n_coords:
            # TODO: Expand dimensions of size one
            raise IndexError("data of wrong dimension (%s, expected %s)" %
                             (data.ndim, self.n_coords))

        if self.acs.shape(data) != self.shape[1:]:
            raise ValueError("data of wrong shape (%s, expected %s)" %
                             (self.acs.shape(data), self.shape[1:]))

        data = np.expand_dims(data, 0)

        # No data is loaded
        if self.loaded.is_empty():
            self.loaded = self.avail.copy()
            self.loaded.var = [var]
            self.data = data

        # Variable is already loaded
        elif var in self.loaded.var:
            self[var][:] = data[0]

        # Variable is not loaded, others are
        else:
            self.loaded.var.append(var)
            self.data = self.acs.concatenate((self.data, data), axis=0)

    def add_variable(self, variable, data=None, **attrs):
        """Add new variable.

        Add variable, and its attributes to the VI.
        If present, add data to loaded data.

        Parameters
        ----------
        variable: str
            Variable to add.
        data: Array, optional
            Corresponding data to add.
            Its shape must match that of the loaded scope.
        attrs: Any, optional
            Variable attributes.
            Passed to VariablesInfo.add_variable
        """
        if variable not in self.vi:
            self.vi.add_variable(variable, **attrs)
        if data is not None:
            self.set_data(variable, data)

    def remove_loaded_variable(self, variable: str):
        """Remove variable from data."""
        if variable in self.loaded:
            keys = self.loaded.idx[variable]
            self.data = np.delete(self.data, [keys], axis=0)
            self.loaded.var.remove(variable)

    def write(self, filename, wd=None, variables=None):
        """Write variables to disk.

        Write to a netcdf file.
        Coordinates are written too.

        Parameters
        ----------
        filename: str
            File to write in. Relative to each filegroup root
            directory, or from `wd` if specified.
        wd: str, optional
            Force to write `filename` in this directory.
        variables: str, List[str], optional
            Variables to write. If None, all are written.
        """
        if variables is None:
            variables = self.loaded.var
        else:
            variables = [v for v in variables if v in self.loaded.var]
        fg_var = self._get_filegroups_for_variables(variables)
        for fg, var_list in fg_var:
            fg.write(filename, wd, var_list)


def subset_slices(key, key_subset):
    """Compound slices and lists when subsetting a coord.

    Parameters
    ----------
    key: Slice or List[int]
        Current slice of a coordinate.
    key_subset: Slice or List[int]
        Asked slice of coordinate.
    """
    key_new = None
    if isinstance(key, list):
        if isinstance(key_subset, slice):
            key_new = key[key_subset]
        if isinstance(key_subset, list):
            key_new = [key[i] for i in key_subset]

    if isinstance(key, slice):
        if isinstance(key_subset, slice):
            key_new = slice(key_subset.start + key.start,
                            key_subset.stop + key.start,
                            key_subset.step * key.step)
        if isinstance(key_subset, list):
            key_new = [i*key.step + key.start for i in key_subset]

    return key_new


def do_post_load_default(dt): #pylint: disable=method-hidden
    """Do post loading treatments.

    Raises
    ------
    NotImplementedError
        If do_post_load was not set.
    """
    raise NotImplementedError("do_post_load was not set.")
