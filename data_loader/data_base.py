"""Base class for data."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


import logging
from typing import Any, Callable, Dict, List, Type, Union

import numpy as np

from data_loader.accessor import Accessor
from data_loader.coordinates.coord import Coord
from data_loader.custom_types import KeyLike, KeyLikeValue, KeyLikeVar
from data_loader.filegroup.filegroup_load import FilegroupLoad
from data_loader.keys.keyring import Keyring
from data_loader.scope import Scope
from data_loader.variables_info import VariablesInfo


log = logging.getLogger(__name__)


class DataBase():
    r"""Encapsulate data array and info about the variables.

    The data itself is stored in the data attribute.
    It can be loaded from disk using multiple `Filegroups`.
    The data can be conveniently accessed using the `view` method.

    The data consists in multiple variables varying along
    multiple coordinates.
    An ensemble of coordinates and variables makes a `Scope`.
    The data object has three different scopes:
    \*avail: all data available on disk
    \*loaded: part of that data that is loaded in memory
    \*selected: part of data selected

    Coordinates objects, the list of variables, the shape
    of data, and other attributes of the different scopes objects,
    are directly accessible from the data object.
    If data has been loaded, the 'loaded' scope is used,
    otherwise the 'available' scope is used.

    Data and coordinates can be accessed as items:
    `Data[name of variable]`.

    See :doc:`../data` for more information.

    :param root: Root data directory containing all files.
    :param vi: Information on the variables and data.
    :param coords: Coordinates, in the order the data should be kept.
        This includes variables.

    Attributes
    ----------
    root: str
        Root data directory containing all files.
    vi: VariablesInfo
        Information on the variables and data.

    coords_name: List[str]
        Coordinates names, in the order the data
        is kept in the array.

    data: np.ndarray or subclass
        Data array if loaded, None otherwise.

    filegroups: List[FilegroupLoad]

    avail: Scope
        Scope of available data (on disk).
    loaded: Scope
        Scope of loaded data.
    selected: Scope
        Scope of selected data.

    acs: Type[Accessor]
        Accessor class (or subclass) to use to access the data.

    do_post_loading: Callable
        Function applied after loading data.
    """

    acs = Accessor

    def __init__(self, root: str,
                 filegroups: List[FilegroupLoad],
                 vi: VariablesInfo,
                 *coords: Coord):
        self.root = root

        self.coords_name = [c.name for c in coords if c.name != 'var']

        self.avail = Scope(coords=coords)
        self.loaded = self.avail.copy()
        self.selected = self.avail.copy()
        self.loaded.empty()
        self.selected.empty()
        self.avail.name = 'available'
        self.loaded.name = 'loaded'
        self.selected.name = 'selected'

        self.filegroups = filegroups

        self.vi = vi

        self.data = None

        self.link_filegroups()

        self.do_post_loading = do_post_loading_default

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

        if self.selected.is_empty():
            s.append('No data selected')
        else:
            s.append('Data selected: \n%s' % str(self.selected))
        s.append('')

        s.append("%d Filegroups:" % len(self.filegroups))
        s += ['\t%s' % ', '.join(fg.variables) for fg in self.filegroups]

        return '\n'.join(s)

    def __repr__(self):
        return '\n'.join([super().__repr__(), str(self)])

    @property
    def bases(self) -> Dict[str, str]:
        """Bases classes.

        Returns dictionary of bases name and their fullname
        (with module).

        :returns: {class name: full name with module}
        """
        bases = self.__class__.__bases__
        out = {c.__name__: '%s.%s' % (c.__module__, c.__name__)
               for c in bases}
        return out

    def _check_loaded(self):
        """Check if data is loaded.

        :raises RuntimeError: If the data is not loaded.
        """
        if self.data is None:
            raise RuntimeError("Data not loaded.")

    def __getitem__(self, y: str):
        """Return a coordinate, or data for a variable.

        If y is a variable name, return the corresponding data slice.

        :param y: Coordinate or variable name.

        :raises KeyError: If key is not a coordinate or variable.
        """
        if isinstance(y, str):
            if y in self.loaded:
                y = self.idx(y)
                return self.data[y]
            raise KeyError("Variable '%s' is not loaded." % y)
        raise TypeError("Key must be a str.")

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

    @property
    def dims(self) -> List[str]:
        """List of dimensions names."""
        return ['var'] + self.coords_name

    def get_scope(self, scope: Union[str, Scope]) -> Scope:
        """Get scope by name."""
        if isinstance(scope, str):
            scope = {'avail': self.avail,
                     'loaded': self.loaded,
                     'selected': self.selected,
                     'current': self.scope}[scope]
        return scope

    def idx(self, variable: str) -> int:
        """Index of variables in the data array.

        Wrapper around loaded Scope.idx()

        Parameters
        ----------
        variable: str, List[str], slice
        """
        return self.loaded.idx(variable)

    def view(self, *keys: KeyLike,
             keyring: Keyring = None, **kw_keys: KeyLike) -> np.ndarray:
        """Returns a subset of loaded data.

        Keys act on loaded scope.
        If a key is an integer, the corresponding dimension in the
        array will be squeezed.

        :param keyring: [opt] Keyring specifying parts of dimensions to take.
        :param keys: [opt] Keys specifying parts of dimensions to take.
            Take precedence over keyring.

        :returns: Subset of data, in storage order.
        """
        self._check_loaded()

        kw_keys = self.get_kw_keys(*keys, **kw_keys)
        keyring = Keyring.get_default(keyring, **kw_keys, variables=self.loaded.var)
        keyring.make_full(self.dims)
        keyring.make_total()
        keyring.simplify()
        keyring.sort_by(self.dims)
        log.debug('Taking keys in data: %s', keyring.print())
        return self.acs.take(keyring, self.data)

    def view_selected(self, scope: Union[str, Scope] = 'selected',
                      keyring: Keyring = None, **keys: KeyLike) -> np.ndarray:
        """Returns a subset of loaded data.

        Subset is specified by a scope.
        One can further slice the selection using keys.

        :param scope: Scope indicating the selection to take.
            It must have been created from the loaded scope.
            Defaults to current selection.
        :param keyring: [opt] Keyring specifying further slicing of selection.
        :param keys: [opt] Keys specifying further slicing of selection.
            Take precedence over keyring.

        :raises KeyError: Selection scope is empty.
        :raises ValueError: Selection scope was not created from loaded.
        """
        scope = self.get_scope(scope)
        if scope.is_empty():
            raise KeyError("Selection scope is empty ('%s')." % scope.name)
        if scope.parent_scope != self.loaded:
            raise ValueError("The parent scope is not the loaded data scope."
                             " (is '%s')" % scope.parent_scope.name)

        scope_ = scope.copy()
        scope_.slice(keyring, int2list=False, **keys)
        return self.view(keyring=scope_.parent_keyring)

    def view_ordered(self, order: List[str],
                     keyring: Keyring = None, **keys: KeyLike) -> np.ndarray:
        """Returns a reordered subset of data.

        The ranks of the array are rearranged to follow
        the specified coordinates order.
        Keys act on loaded scope.

        :param order: List of dimensions names in required order.
            Either two dimensions (for swapping them)
            or all of them should be specified.
        :param keyring: [opt] Keyring specifying parts of dimensions to take.
        :param keys: [opt] Keys specifying parts of dimensions to take.
            Take precedence over keyring.

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
        view: For details on subsetting data (without reordering).
        """
        self._check_loaded()

        keyring = Keyring.get_default(keyring, **keys, variables=self.loaded.var)
        keyring.make_full(self.dims)
        keyring.make_total()
        keyring.sort_by(self.dims)

        log.debug('Taking keys in data: %s', keyring.print())
        array = self.acs.take(keyring, self.data)
        # TODO: log reorder
        return self.acs.reorder(keyring, array, order)

    def iter_slices(self, coord: str, size: int = 12,
                    key: KeyLike = None) -> List[KeyLike]:
        """Iter through slices of a coordinate.

        Scope will be loaded if not empty, available otherwise.
        The prescribed slice size is a maximum, the last
        slice can be smaller.

        :param coord: Coordinate to iterate along to.
        :param size: [opt] Size of the slices to take.
        :param key: [opt] Subpart of coordinate to iter through.
        """
        return self.scope.iter_slices(coord, size, key)

    def iter_slices_month(self, coord: str = 'time',
                          key: KeyLike = None) -> List[List[int]]:
        """Iter through monthes of a time coordinate.

        :param coord: [opt] Coordinate to iterate along to.
            Must be subclass of Time.
        :param key: [opt] Subpart of coordinate to iter through.

        See also
        --------
        iter_slices: Iter through any coordinate
        """
        return self.scope.iter_slices_month(coord, key)

    def link_filegroups(self):
        """Link filegroups and data."""
        for fg in self.filegroups:
            fg.db = self
            fg.acs = self.acs

    @property
    def ndim(self) -> int:
        """Number of dimensions."""
        return len(self.dims)

    @property
    def ncoord(self) -> int:
        """Number of coordinates."""
        return len(self.coords_name)

    @property
    def shape(self) -> List[int]:
        """Shape of the data from current scope.

        Scope is loaded if not empty, available otherwise.
        """
        return self.scope.shape

    def get_limits(self, *coords: str,
                   scope: Union[str, Scope] = 'current',
                   keyring: Keyring = None, **keys: KeyLike) -> List[float]:
        """Return limits of coordinates.

        Min and max values for specified coordinates.
        Scope is loaded if not empty, available otherwise.

        :param coords: [opt] Coordinates name.
            If None, defaults to all coordinates, in the order
            of data.
        :param scope: [opt] Scope to use. Default is current.
        :param keyring: [opt] Subset coordinates.
        :param keys: [opt] Subset coordinates.
            Take precedence over keyring.

        :returns: Min and max of each coordinate. Flattened.

        Examples
        --------
        >>> print(dt.get_limits('lon', 'lat'))
        [-20.0 55.0 10.0 60.0]

        >>> print(dt.get_extent(lon=slice(0, 10)))
        [-20.0 0.]
        """
        scope = self.get_scope(scope)
        return scope.get_limits(*coords, keyring=keyring, **keys)

    def get_extent(self, *coords: str,
                   scope: Union[str, Scope] = 'current',
                   keyring: Keyring = None, **keys: KeyLike) -> List[float]:
        """Return extent of loaded coordinates.

        Return first and last value of specified coordinates.

        :param coords: [opt] Coordinates name.
            If None, defaults to all coordinates, in the order
            of data.
        :param scope: [opt] Scope to use. Default is current.
        :param keyring: [opt] Subset coordinates.
        :param keys: [opt] Subset coordinates.
            Take precedence over keyring.

        :returns: First and last values of each coordinate.

        Examples
        --------
        >>> print(dt.get_extent('lon', 'lat'))
        [-20.0 55.0 60.0 10.0]

        >>> print(dt.get_extent(lon=slice(0, 10)))
        [-20.0 0.]
        """
        scope = self.get_scope(scope)
        return scope.get_extent(*coords, keyring=keyring, **keys)

    def get_kw_keys(self, *keys: KeyLike, **kw_keys: KeyLike) -> Dict[str, KeyLike]:
        """Make keyword keys when asking for coordinates parts.

        From a mix of positional and keyword argument,
        make a list of keywords.
        Keywords arguments take precedence over positional arguments.
        Positional argument shall be ordered as the coordinates
        are ordered in data.

        :param keys: [opt]
        :param kw_keys: [opt]

        Exemples
        --------
        >>> print( dt.get_kw_keys([0, 1], lat=slice(0, 10)) )
        {'time': [0, 1], 'lat': slice(0, 10)}
        """
        for i, key in enumerate(keys):
            name = self.dims[i]
            if name not in kw_keys:
                kw_keys[name] = key
        return kw_keys

    def get_subscope(self, scope: Union[str, Scope] = 'avail',
                     keyring: Keyring = None, int2list: bool = True,
                     **keys: KeyLike) -> Scope:
        """Return subset of scope.

        :param scope: [opt] Scope to subset.
            If str, can be {'avail', 'loaded', 'selected'},
            corresponding scope of data will then be taken.
        :param keyring: [opt]
        :param keys: [opt]

        :returns: Copy of input scope, sliced with specified keys.
        """
        scope = self.get_scope(scope)
        subscope = scope.copy()
        subscope.reset_parent_keyring()
        subscope.parent_scope = scope
        subscope.slice(keyring, int2list=int2list, **keys)
        return subscope

    def select(self, scope: Union[str, Scope] = 'current',
               keyring: Keyring = None, **keys: KeyLike):
        """Set selected scope from another scope.

        Wrapper around :func:`get_subscope`.

        :param scope: [opt] Scope to subset.
            If str, can be {'avail', 'loaded', 'selected'},
            corresponding scope of data will then be taken.
        :param keyring: [opt]
        :param keys: [opt]

        Examples
        --------
        >>> dt.select(var='sst', time=20)
        >>> dt.select('loaded', lat=slice(10, 30))

        See also
        --------
        get_subscope
        """
        self.selected = self.get_subscope(scope, keyring,
                                          int2list=False, **keys)
        self.selected.name = 'selected'

    def select_by_value(self, scope: Union[str, Scope] = 'current',
                        **keys: KeyLikeValue):
        """Select by value.

        :param scope: [opt] Scope to select from.
        :param keys: [opt]

        See also
        --------
        load_by_value:
           Similar management of keys arguments.
        """
        scope = self.get_scope(scope)
        keys_ = {}
        for name, key in keys.items():
            c = scope[name]
            if isinstance(key, slice):
                key = c.subset(key.start, key.stop)
            elif isinstance(key, (list, tuple, np.ndarray)):
                key = [c.get_index(k) for k in key]
            else:
                key = c.get_index(key)
            keys_[name] = key
        self.select(scope, **keys_)

    def add_to_selection(self, scope: Union[str, Scope] = 'avail',
                         keyring: Keyring = None, **keys: KeyLike):
        """Add to selection.

        Keys act upon the parent scope of selection.
        TODO: Keys are always sorted in increasing order

        :param Scope: [opt] If nothing was selected before, select keys from this scope.
        :param keyring: [opt]
        :param keys: [opt]
        """
        scope = self.selected
        if scope.is_empty():
            self.select(scope, keyring=keyring, **keys)
        else:
            keyring = Keyring.get_default(keyring, **keys, variables=self.avail.var)
            keyring.set_shape(scope.parent_scope.dims)
            keyring = keyring + scope.parent_keyring
            keyring.sort_keys()
            keyring.simplify()
            self.select(scope=scope.parent_scope, keyring=keyring)

    def slice_data(self, keyring: Keyring = None, **keys: KeyLike):
        """Slice loaded data.

        Keys act on loaded scope.

        :param keyring: [opt]
        :param keys: [opt]
        """
        self._check_loaded()
        keyring = Keyring.get_default(keyring, **keys)
        keyring.make_int_list()
        self.loaded = self.get_subscope('loaded', keyring)
        self.data = self.view(keyring=keyring)

    def unload_data(self):
        """Remove data."""
        self.data = None
        self.loaded.empty()

    def load_by_value(self, *keys: KeyLikeValue, **kw_keys: KeyLikeValue):
        """Load part of data from disk into memory.

        Part of the data to load is specified by values.

        :param keys: [opt] Values to select for a coordinate.
            If is slice, use start and stop as boundaries. Step has no effect.
            If is float, int, or a list of, closest index for each value is taken.
        :param kw_keys: [opt] Same.

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
        kw_keys = self.get_kw_keys(*keys, **kw_keys)
        for name, c in self.avail.dims.items():
            key = kw_keys.get(name)
            if key is None:
                key = slice(None, None)
            elif isinstance(key, slice):
                key = c.subset(key.start, key.stop)
            elif isinstance(key, (list, tuple, np.ndarray)):
                key = [c.get_index(k) for k in key]
            else:
                key = c.get_index(key)
            keys_[name] = key
        self.load(**keys_)

    def load(self, *keys: KeyLike, **kw_keys: KeyLike):
        """Load part of data from disk into memory.

        What variables, and what part of the data
        corresponding to coordinates indices can be specified.
        Keys specified to subset data act on the available scope.
        If a parameter is None, all available is taken for that
        parameter.

        :param keys: [opt] What subset of coordinate to load.
            The order is that of self.coords.
        :param kw_keys: [opt] What subset of coordinate to load. Takes precedence
            over positional `coords`.
            Variables key argument should be named 'var'.

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
        keyring.make_full(self.dims)
        keyring.make_total()
        keyring.make_int_list()
        keyring.make_var_idx(self.avail.var)
        keyring.sort_by(self.dims)

        self.loaded = self.get_subscope('avail', keyring)
        self.loaded.name = 'loaded'

        self.self_allocate(self.loaded.shape)

        loaded = any([fg.load_from_available(keyring)
                      for fg in self.filegroups])
        if not loaded:
            log.warning("Nothing loaded.")

        try:
            self.do_post_loading(self)
        except NotImplementedError:
            pass

    def load_selected(self, keyring: Keyring = None,
                      scope: Union[str, Scope] = 'selected',
                      **keys: KeyLike):
        """Load data from a child scope of available.

        Subset is specified by a scope.
        The selection scope is expected to be created from
        the available one.

        :param keyring: [opt]
        :param scope: [opt] Selected scope created from available scope.
            Defaults to `self.selected`.
        :param keys: [opt]

        :raises KeyError: Selection scope is empty.
        :raises ValueError: Selection scope was not created from available.
        """
        if scope is None:
            scope = self.selected
        if scope.is_empty():
            raise KeyError("Selection scope is empty ('%s')." % scope.name)
        if scope.parent_scope != self.avail:
            raise ValueError("The parent scope is not the available data scope."
                             " (is '%s')" % scope.parent_scope.name)

        scope_ = scope.copy()
        scope_.slice(int2list=False, keyring=keyring, **keys)
        self.load(**scope_.parent_keyring.kw)

    def allocate(self, shape: List[int]) -> np.ndarray:
        """Allocate data array.

        :param shape: Shape of the array to allocate.
        """
        log.info("Allocating numpy array of shape %s", shape)
        return self.acs.allocate(shape)

    def self_allocate(self, shape: List[int]):
        """Allocate data array for itself.

        :param shape: Shape of the array to allocate.
        """
        self.data = self.allocate(shape)

    def set_post_loading_func(self, func: Callable[[Type["DataBase"]], None]):
        """Set function for post loading treatements.

        :param func: Function to execute after data is loaded.
            See do_post_loading() for a better description
            of the function interface.

        """
        self.do_post_loading = func

    def set_data(self, variable: str, data: np.ndarray):
        """Set the data for a single variable.

        :param var: Variable to set the data to.
        :param data: Array of the correct shape for currently
            selected coordinates. Has no axis for variables.

        :raises KeyError: If the variable is not in available scope.
        :raises IndexError: If the data has not the right dimension.
        :raises ValueError: If the data is not of the shape of loaded scope.
        """
        if variable not in self.avail:
            raise KeyError("%s is not in avail scope. Use add_variable." % variable)
        if self.acs.ndim(data) != self.ncoord:
            raise IndexError("data of wrong dimension (%s, expected %s)" %
                             (data.ndim, self.ncoord))
        if self.acs.shape(data) != self.shape[1:]:
            raise ValueError("data of wrong shape (%s, expected %s)" %
                             (self.acs.shape(data), self.shape[1:]))

        data = np.expand_dims(data, 0)

        # No data is loaded
        if self.loaded.is_empty():
            self.loaded = self.avail.copy()
            self.loaded.var.update_values([var])
            self.data = data

        # Variable is already loaded
        elif var in self.loaded.var:
            self[var][:] = data[0]

        # Variable is not loaded, others are
        else:
            self.loaded.var.append(var)
            self.data = self.acs.concatenate((self.data, data), axis=0)

    def add_variable(self, variable: str, data: np.ndarray = None, **attrs: Any):
        """Add new variable.

        Add variable to available scope,
        and its attributes to the VI.
        If present, add data to loaded data.

        :param variable: Variable to add.
        :param data: [opt] Corresponding data to add.
            Its shape must match that of the loaded scope.
        :param attrs: [opt] Variable attributes.
            Passed to VariablesInfo.add_variable
        """
        if variable not in self.vi:
            self.vi.set_attrs(variable, **attrs)
            self.avail.var.append(variable)
        if data is not None:
            self.set_data(variable, data)

    def remove_loaded_variable(self, variable: str):
        """Remove variable from data."""
        if variable in self.loaded:
            keys = self.loaded.idx[variable]
            self.data = np.delete(self.data, [keys], axis=0)
            self.loaded.var.remove(variable)

    def write(self, filename: str, wd: str = None, **keys: KeyLike):
        """Write variables to disk.

        Write to a netcdf file.
        Coordinates are written too.

        :param filename: File to write in. Relative to each filegroup root
            directory, or from `wd` if specified.
        :param wd: [opt] Force to write `filename` in this directory.
        :param variables: [opt] Variables to write. If None, all are written.
        """
        keyring = Keyring(**keys)
        keyring.make_full(self.dims)
        keyring.make_total()
        keyring['var'] = self.loaded.var.get_var_names(keyring['var'])

        for fg in self.filegroups:
            variables = [v for v in keyring['var']
                         if v in fg.variables]
            if variables:
                keyring_fg = keyring.copy()
                keyring_fg['var'] = variables
                fg.write(filename, wd, keyring=keyring_fg)

    def write_add_variable(self, var: str, sibling: str,
                           inf_name: KeyLikeVar = None, **keys: KeyLike):
        """Add variables to files.

        :param var: Variable to add. Must be in loaded scope.
        :param sibling: Variable along which to add the data.
            New variable will be added to the same files
            and in same order.
        :param inf_name: [opt] Variable in-file name. Default to the variables name.
        :param keys: [opt] If a subpart of data is to be written.
            The selected data must match in shape that of the
            sibling data on disk.
        """
        if inf_name is None:
            inf_name = var
        scope = self.get_subscope('loaded', var=var, **keys)
        for fg in self.filegroups:
            if sibling in fg.variables:
                fg.write_add_variable(var, sibling, inf_name, scope)
                break


def do_post_loading_default(dt: DataBase): #pylint: disable=method-hidden
    """Do post loading treatments.

    :raises NotImplementedError: If do_post_loading was not set.
    """
    raise NotImplementedError("do_post_loading was not set.")
