"""Base class for data."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import logging
from typing import Any, Dict, List, Tuple, Type, Union

import numpy as np

from tomate.coordinates.coord import Coord
from tomate.custom_types import Array, KeyLike, KeyLikeInt, KeyLikeValue
from tomate.filegroup.filegroup_load import FilegroupLoad
from tomate.keys.keyring import Keyring
from tomate.scope import Scope
from tomate.variables.base import Variable
from tomate.variables_info import VariablesInfo


log = logging.getLogger(__name__)


class DataBase():
    r"""Encapsulate data array and info about the variables.

    The data itself is stored in the data attribute.
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

    :param vi: Information on the variables and data.
    :param dims: Dimensions, (ie subclasses of Coord)
        in the order the data should be kept.
        This includes variables.
        They are linked (not copied) to the available
        scope.

    :attr dims: List[str]: Dimensions names,
        in the order the data is kept in the array.

    :attr vi: VariablesInfo: Information on the variables and data.
    :attr data: np.ndarray or subclass: Data array if loaded, None otherwise.
    :attr avail: Scope: Scope of available data (on disk).
    :attr loaded: Scope: Scope of loaded data.
    :attr selected: Scope: Scope of selected data.
    """

    def __init__(self, dims: List[Coord],
                 vi: VariablesInfo = None):

        self.dims = [c.name for c in dims]

        self.avail = Scope(dims=dims, copy=False)
        self.loaded = self.avail.copy()
        self.selected = self.avail.copy()
        self.loaded.empty()
        self.selected.empty()
        self.avail.name = 'available'
        self.loaded.name = 'loaded'
        self.selected.name = 'selected'

        if vi is None:
            vi = VariablesInfo()
        self.vi = vi

        self.variables = {}

    @property
    def coords(self) -> List[str]:
        """Coordinates names. """
        return [d for d in self.dims if d != 'var']

    def __repr__(self):
        s = ["Data object"]

        s.append("Class: {}, Bases: {} ".format(self.__class__.__name__,
                                                ', '.join(self.bases.keys())))
        s.append('')
        s.append("Data available: \n{}".format(repr(self.avail)))
        s.append('')

        if self.loaded.is_empty():
            s.append('Data not loaded')
        else:
            s.append('Data loaded: \n{}'.format(repr(self.loaded)))
        s.append('')

        if self.selected.is_empty():
            s.append('No data selected')
        else:
            s.append('Data selected: \n{}'.format(repr(self.selected)))
        s.append('')

        return '\n'.join(s)

    @property
    def bases(self) -> Dict[str, str]:
        """Bases classes.

        Returns dictionary of bases name and their fullname
        (with module).

        :returns: {class name: full name with module}
        """
        bases = self.__class__.__bases__
        out = {c.__name__: '{}.{}'.format(c.__module__, c.__name__)
               for c in bases}
        return out

    def get_filegroup(self, key: Union[int, str]) -> FilegroupLoad:
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

    def check_loaded(self):
        """Check if data is loaded.

        :raises RuntimeError: If the data is not loaded.
        """
        if self.loaded.is_empty():
            raise RuntimeError("Data not loaded.")

    def __getitem__(self, key: str) -> Variable:
        """Return a coordinate, or data for a variable.
        """
        if isinstance(key, str):
            return self.variables[key]
        raise TypeError("Key must be a str.")

    def __setitem__(self, key: str, value: Array):
        """Assign data to a variable.

        Wrapper around set_data
        """
        self.variables[key].set_data(value)

    def __getattribute__(self, name):
        """Get attribute.

        If `name` is a coordinate name, return coordinate from
        current scope.
        If `name` is 'var', return list of variable from
        current scope.
        """
        if name in super().__getattribute__('dims'):
            if not self.loaded.is_empty():
                scope = super().__getattribute__('loaded')
            else:
                scope = super().__getattribute__('avail')
            return scope[name]
        return super().__getattribute__(name)

    @property
    def scope(self) -> Scope:
        """Loaded scope if not empty, available scope otherwise."""
        if not self.loaded.is_empty():
            return self.loaded
        return self.avail

    def get_scope(self, scope: Union[str, Scope]) -> Scope:
        """Get scope by name."""
        if isinstance(scope, str):
            scope = {'avail': self.avail,
                     'loaded': self.loaded,
                     'selected': self.selected,
                     'current': self.scope}[scope]
        return scope

    def view(self, *keys: KeyLike, keyring: Keyring = None,
             stack: str = None, order: List[str] = None,
             **kw_keys: KeyLike) -> Union[Array, Tuple[Array]]:
        """Returns a subset of loaded data.

        Keys act on loaded scope.
        If a key is an integer, the corresponding dimension in the
        array will be squeezed.
        If multiple variables are asked, a tuple containing each variable
        data is returned. Multiple variables can also be stacked in the
        same array. Data dimensions can be reordered

        :param keyring: [opt] Keyring specifying parts of dimensions to take.
        :param keys: [opt] Keys specifying parts of dimensions to take, in
            the order dimensions are stored. Take precedence over `keyring`.
        :param kw_keys: [opt] Argument name is dimension name. Takes precedence
            over `keys`.
        :param stack: [opt] Concatenate different variables into one array.
            If is True, concatenate variables if they all have the same datatype
            and dimensions. If equal to 'force', will concatenate even if
            datatypes are different. Order of concatenation follow the variable
            key. The first variable accessor is used for concatenation.
        :param order: [opt] Reorder data dimensions. If of length 2,
            the two dimensions will be swapped. Otherwise, '`order`'
            must contain all the dimensions of the variable.
            When stacking data, the order must contain all dimensions,
            including 'var'. Squeezed dimensions are not taken into account.

        :returns: Subset of data.
        :raises RuntimeError: If the user ask for an impossible stack
        """
        self.check_loaded()

        kw_keys = self.get_kw_keys(*keys, **kw_keys)
        keyring = Keyring.get_default(keyring, **kw_keys)
        keyring.make_full(self.dims)
        keyring.make_total()
        keyring.make_idx_str(var=self.loaded.var)

        variables = [self.variables[var] for var in keyring['var']]
        dims = [[d for d in self.variables[var].dims
                 if d in keyring.get_non_zeros()]
                for var in keyring['var']]

        do_stack = (stack and len(variables) > 1
                    and all([set(d) == set(dims[0]) for d in dims[1:]])
                    and (stack == 'force'
                         or all([v.datatype == variables[0].datatype
                                 for v in variables[1:]])))

        if stack and not do_stack:
            raise RuntimeError("Cannot stack variables")

        if order is not None:
            order_novar = [d for d in order if d != 'var']
        else:
            order_novar = None

        out = tuple([var.view(keyring, order=order_novar) for var in variables])
        if do_stack:
            if order is not None:
                axis_stack = order.index('var')
            else:
                axis_stack = self.dims.index('var')
            out = variables[0].acs.stack(out, axis=axis_stack)
        elif keyring['var'].size == 0:
            out = out[0]

        return out

    def view_by_value(self, *keys: KeyLikeInt,
                      by_day: bool = False,
                      stack: Union[str, bool] = None,
                      order: List[str] = None,
                      **kw_keys: KeyLike) -> np.ndarray:
        """Returns a subset of loaded data.

        Arguments work similarly as
        :func:`DataDisk.load_by_value
        <tomate.db_types.data_disk.DataDisk.load_by_value>`.

        See also
        --------
        view
        """
        self.check_loaded()
        kw_keys = self.get_kw_keys(*keys, **kw_keys)
        keyring = self.loaded.get_keyring_by_index(by_day=by_day, **kw_keys)
        return self.view(keyring=keyring, stack=stack, order=order)

    def view_selected(self, scope: Union[str, Scope] = 'selected',
                      stack: Union[str, bool] = None, order: List[str] = None,
                      keyring: Keyring = None, **keys: KeyLike) -> np.ndarray:
        """Returns a subset of loaded data.

        Subset to view is specified by a scope.
        The selection can be sliced further by specifying keys.

        :param scope: Scope indicating the selection to take.
            If str, can be {'avail', 'loaded', 'selected', 'current'},
            corresponding scope will then be taken.
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
            raise KeyError(f"Selection scope is empty ('{scope.name}').")
        if scope.parent_scope != self.loaded:
            raise ValueError("The parent scope is not the loaded data scope."
                             f" (is '{scope.parent_scope.name}')")

        scope_ = scope.copy()
        scope_.slice(keyring, int2list=False, **keys)
        return self.view(keyring=scope_.parent_keyring, stack=stack, order=order)

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

    @property
    def ndim(self) -> int:
        """Number of dimensions."""
        return len(self.dims)

    @property
    def ncoord(self) -> int:
        """Number of coordinates."""
        return len(self.coords)

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
        >>> print(db.get_limits('lon', 'lat'))
        [-20.0 55.0 10.0 60.0]

        >>> print(db.get_extent(lon=slice(0, 10)))
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
        >>> print(db.get_extent('lon', 'lat'))
        [-20.0 55.0 60.0 10.0]

        >>> print(db.get_extent(lon=slice(0, 10)))
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

        Examples
        --------
        >>> print( db.get_kw_keys([0, 1], lat=slice(0, 10)) )
        {'time': [0, 1], 'lat': slice(0, 10)}
        """
        for i, key in enumerate(keys):
            name = self.dims[i]
            if name not in kw_keys:
                kw_keys[name] = key
        return kw_keys

    def get_subscope(self, scope: Union[str, Scope] = 'avail',
                     keyring: Keyring = None, int2list: bool = True,
                     name: str = None,
                     **keys: KeyLike) -> Scope:
        """Return subset of scope.

        :param scope: [opt] Scope to subset.
            If str, can be {'avail', 'loaded', 'selected', 'current'},
            corresponding scope of data will then be taken.
        :param keyring: [opt]
        :param keys: [opt]

        :returns: Copy of input scope, sliced with specified keys.
        """
        scope = self.get_scope(scope)
        subscope = scope.copy()
        if name is not None:
            subscope.name = name
        subscope.reset_parent_keyring()
        subscope.parent_scope = scope
        subscope.slice(keyring, int2list=int2list, **keys)
        return subscope

    def get_subscope_by_value(self, scope: Union[str, Scope] = 'avail',
                              int2list: bool = True,
                              name: str = None,
                              by_day: bool = False,
                              **keys: KeyLikeValue) -> Scope:
        """Return subset of scope.

        :param bool: Use `subset_by_day` for Time dimension rather than `subset`.
            Default to False.
        :param kw_keys: [opt] Argument name is dimension name for value selection,
            or dimension name appended with `_idx` for index selection.
        """
        scope = self.get_scope(scope)
        keyring = scope.get_keyring_by_index(by_day=by_day, **keys)
        return self.get_subscope(scope, keyring, int2list, name)

    def select(self, scope: Union[str, Scope] = 'current',
               keyring: Keyring = None, **keys: KeyLike):
        """Set selection scope.

        :param scope: [opt] Scope to select from.
            If str, can be {'avail', 'loaded', 'selected', 'current'},
            corresponding scope will then be taken.
            Default to current scope (loaded if data has been loaded,
            avail otherwise).
        :param keyring: [opt] Keyring specifying parts of dimensions to take.
        :param keys: [opt] Keys specifying parts of dimensions to take.
            Act on the specified scope. Take precedence over `keyring`.

        Examples
        --------
        >>> db.select(var='sst', time=20)
        >>> db.select('loaded', lat=slice(10, 30))

        See also
        --------
        get_subscope: select() is a wrapper around get_subscope().
        """
        self.selected = self.get_subscope(scope, keyring, int2list=False,
                                          name='selected', **keys)

    def select_by_value(self, scope: Union[str, Scope] = 'current',
                        by_day: bool = False, **keys: KeyLike):
        """Set selection scope by value.

        :param scope: [opt] Scope to select from. See `select()`.
        :param by_day: If True, find indices prioritising dates.
            See :ref:`Some examples of coordinates subclasses` for details.
        :param keys: [opt] Keys specifying parts of dimensions to take
            by value. Take precedence over `keyring`. Act on specified scope.
            See 'kw_keys' argument of :func:`DataDisk.load_by_value
            <tomate.db_types.data_disk.DataDisk.load_by_value>` for details.

        Examples
        --------
        >>> db.select_by_value(var='sst', time=[[2007, 4, 21]])
        >>> db.select_by_value('loaded', lat=slice(10, 30), time_idx=0)

        See also
        --------
        select
        get_subscope_by_value: select_by_value() is a wrapper around
            get_subscope_by_value().
        """
        self.selected = self.get_subscope_by_value(scope, int2list=True,
                                                   by_day=by_day,
                                                   name='selected', **keys)

    def add_to_selection(self, scope: Union[str, Scope] = 'avail',
                         keyring: Keyring = None, **keys: KeyLike):
        """Add to selection.

        Keys act on the parent scope of selection.
        Keys are always sorted in increasing order

        :param Scope: [opt] If nothing was selected before, select keys from this scope.
        :param keyring: [opt]
        :param keys: [opt]
        """
        scope = self.selected
        if scope.is_empty():
            self.select(scope, keyring=keyring, **keys)
        else:
            keyring = Keyring.get_default(keyring, **keys, dims=self.avail.dims)
            keyring.set_shape(scope.parent_scope.dims)
            keyring = keyring + scope.parent_keyring
            keyring.sort_keys()
            keyring.simplify()
            self.select(scope=scope.parent_scope, keyring=keyring)

    def slice_data(self, keyring: Keyring = None, **keys: KeyLike):
        """Slice loaded data.

        Keys act on loaded scope.
        """
        self.check_loaded()
        keyring = Keyring.get_default(keyring, **keys)
        keyring.make_int_list()
        self.loaded = self.get_subscope('loaded', keyring)
        self.data = self.view(keyring=keyring)

    def unload_data(self):
        """Remove data."""
        self.data = None
        self.loaded.empty()

    def set_data(self, variable: str, data: np.ndarray,
                 keyring: Keyring = None):
        """Set the data for a single variable.

        :param var: Variable to set the data to.
        :param data: Array of the correct shape for currently
            selected coordinates. Has no axis for variables.
        :param keyring: [opt] If no data is loaded, loaded scope
            is fetched from available scope with this keyring.
            'var' key has no effect.

        :raises KeyError: If the variable is not in available scope.
        :raises IndexError: If the data has not the right dimension.
        :raises ValueError: If the data is not of the shape of loaded scope.
        """
        def check_shape(data):
            if self.acs.shape(data)[1:] != self.shape[1:]:
                raise ValueError("data of wrong shape ({}, expected {})"
                                 .format(self.acs.shape(data)[1:], self.shape[1:]))

        if variable not in self.avail:
            raise KeyError(f"{variable} is not in avail scope. Use add_variable.")
        if self.acs.ndim(data) != self.ncoord:
            raise IndexError("data of wrong dimension ({}, expected {})"
                             .format(data.ndim, self.ncoord))

        data = np.expand_dims(data, 0)

        # No data is loaded
        if self.loaded.is_empty():
            self.loaded = self.get_subscope('avail', keyring=keyring, var=variable)
            check_shape(data)
            self.data = data

        # Variable is already loaded
        elif variable in self.loaded.var:
            check_shape(data)
            self[variable][:] = data[0]

        # Variable is not loaded, others are
        else:
            self.loaded.var.append(variable)
            check_shape(data)
            self.data = self.acs.concatenate((self.data, data), axis=0)

    def add_variable(self, variable: str,
                     coords: List[str] = None,
                     data: Array = None,
                     var_class: Type = None,
                     **attrs: Any):
        if coords is None:
            coords = self.coords
        if variable in self.variables:
            log.warning('%s already in variables, it will be overwritten',
                        variable)
        else:
            if var_class is None:
                var_class = self.vi.get_attr_safe('class', variable, Variable)
            self.variables[variable] = var_class(variable, coords, self)

        if variable not in self.avail:
            self.avail.var.append(variable)

        if data is not None:
            self.variables[variable].set_data(data)

        if self.vi.has('datatype', variable):
            datatype = self.vi.get_attr('datatype', variable)
            self.variables[variable].datatype = datatype

    def remove_loaded_variable(self, variables: Union[str, List[str]]):
        """Remove variable from data."""
        if isinstance(variables, str):
            variables = [variables]
        keep = [v for v in self.loaded if v not in variables]
        self.slice_data(var=keep)
