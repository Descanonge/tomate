"""Base class for data."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import logging
from typing import Any, Dict, List, Tuple, Type, Union, TYPE_CHECKING

from tomate.coordinates.coord import Coord
from tomate.coordinates.variables import Variables
from tomate.custom_types import Array, KeyLike, KeyLikeValue
from tomate.keys.keyring import Keyring
from tomate.scope import Scope
from tomate.variable_base import Variable
from tomate.variables_info import VariablesInfo

if TYPE_CHECKING:
    from tomate.db_types.data_disk import DataDisk


log = logging.getLogger(__name__)


class DataBase():
    r"""Encapsulate all elements of a database.

    The DataBase object contains the scopes for available, loaded, and selected
    data. It is the primary object to modify thoses scope (by loading or
    selecting data for instance). Many methods use the current scope by default,
    *ie* the loaded scope if data is loaded, available scope otherwise.
    Coordinates of the current scope are available as attributes.

    Tha DataBase object also contains one or more Variable object. Those are
    accessible as items with `Data[name of variable]`. Data can be retrieved
    directly with the view method, eventually for multiple variable at once.

    See :doc:`../data` for more information.

    :param dims: Dimensions, (ie subclasses of Coord). Variables can be omitted.
        The dimensions will be stored in various scopes in the order they
        are supplied. This same order is used in many methods when specifying
        keys. They are linked (not copied) to the available scope.
    :param vi: [opt] Information on the variables and data.
        If None, one is created.

    :attr dims: List[str]: Dimensions names in order.
    :attr vi: VariablesInfo: Information on the variables and data.
    :attr avail: Scope: Scope of available data (on disk).
    :attr loaded: Scope: Scope of loaded data.
    :attr selected: Scope: Scope of selected data.
    :attr variables: Dict[Variable]: Variable objects
    :attr var_disk: set: Variables on disk.
    """

    def __init__(self, dims: List[Coord],
                 vi: VariablesInfo = None):

        if not any(d.name == 'var' for d in dims):
            dims.insert(0, Variables([]))
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

        self.var_disk = set()
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
        if self.variables:
            s.append('Variables:')
            for v in self.variables.values():
                z = v.name
                if not type(v) is Variable:
                    z += ' ({}) '.format(type(v).__name__)
                z += ' [{}] '.format(', '.join(v.dims))
                if v.is_loaded():
                    z += ', (loaded)'
                s.append(z)
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

    def check_loaded(self):
        """Raises if data is not loaded.

        :raises RuntimeError: If the data is not loaded.
        """
        if self.loaded.is_empty():
            raise RuntimeError("Data not loaded.")

    def __getitem__(self, key: KeyLike) -> Variable:
        """Return a variable object. """
        if isinstance(key, str):
            return self.variables[key]
        raise TypeError("Key must be a str.")

    def __setitem__(self, key: str, value: Array):
        """Assign data to a variable.

        Wrapper around Variable.set_data
        """
        self.variables[key].set_data(value, Keyring())

    def __getattribute__(self, name: str):
        """Get attribute.

        If `name` is a coordinate name, return coordinate from
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
        """Get scope by name.

        :param scope: Can be {'avail', 'loaded', 'selected', 'current'},
            or a Scope object, which will simply be returned.
        """
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
            the order dimensions are stored in. Take precedence over `keyring`.
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
        kw_keys = self.get_kw_keys(*keys, **kw_keys)
        keyring = Keyring.get_default(keyring, **kw_keys)
        keyring.make_full(self.dims)
        keyring.make_total()
        keyring.make_idx_str(var=self.loaded.var)

        variables = [self.variables[var] for var in keyring['var']]
        dims = [[d for d in self.variables[var].dims
                 if d in keyring.get_non_zeros()]
                for var in keyring['var']]

        if stack and len(variables) > 1:
            if not all(v in self.loaded.var for v in keyring['var']):
                raise RuntimeError("Cannot stack variables"
                                   " (variable not loaded)")
            if (stack != 'force'
                and not all(v.datatype == variables[0].datatype
                            for v in variables[1:])):
                raise RuntimeError("Cannot stack variables"
                                   " (different datatypes)")
            if (order is None and not all(d == dims[0] for d in dims[1:])):
                raise RuntimeError("Cannot stack variables (different "
                                   "dimensions or order not specified)")
            if (order is not None and not all(set(d) == set(dims[0])
                                              for d in dims[1:])):
                raise RuntimeError("Cannot stack variables"
                                   " (different dimensions)")

        if order is not None:
            order_novar = [d for d in order if d != 'var']
        else:
            order_novar = None

        out = tuple([var.view(keyring=keyring, order=order_novar)
                     for var in variables])
        if stack:
            if order is not None:
                axis_stack = order.index('var')
            else:
                axis_stack = self.dims.index('var')
            out = variables[0].acs.stack(out, axis=axis_stack)
        elif keyring['var'].size == 0:
            out = out[0]

        return out

    def view_by_value(self, *keys: KeyLike, by_day: bool = False,
                      stack: Union[str, bool] = None, order: List[str] = None,
                      **kw_keys: KeyLike) -> Union[Array, Tuple[Array]]:
        """Returns a subset of loaded data.

        Arguments work similarly as :func:`DataDisk.load_by_value
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
                      keyring: Keyring = None,
                      **keys: KeyLike) -> Union[Array, Tuple[Array]]:
        """Returns a subset of loaded data.

        Subset to view is specified by a scope.
        The selection can be sliced further by specifying keys.

        :param scope: Scope indicating the selection to take.
            If str, can be {'avail', 'loaded', 'selected', 'current'},
            corresponding scope will then be taken. It must have been
            created from the loaded scope. Defaults to current selection.
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

        :param coords: [opt] Coordinates name.
            If None, defaults to all coordinates in order.
        :param scope: [opt] Scope to use. Default is current.
        :param keyring: [opt] Subset coordinates.
        :param keys: [opt] Subset coordinates. Take precedence over keyring.

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
            If None, defaults to all coordinates, in the order.
        :param scope: [opt] Scope to use. Default is current.
        :param keyring: [opt] Subset coordinates.
        :param keys: [opt] Subset coordinates. Take precedence over keyring.

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

        From a mix of positional and keyword argument, make a list of keywords.
        Keywords arguments take precedence over positional arguments.
        Positional argument shall be ordered as the coordinates
        are ordered in data.

        Examples
        --------
        >>> print( db.get_kw_keys('SST', [0, 1], lat=slice(0, 10)) )
        {'var': 'SST', 'time': [0, 1], 'lat': slice(0, 10)}
        """
        for i, key in enumerate(keys):
            name = self.dims[i]
            if name not in kw_keys:
                kw_keys[name] = key
        return kw_keys

    def get_subscope(self, scope: Union[str, Scope] = 'avail',
                     keyring: Keyring = None, int2list: bool = True,
                     name: str = None, **keys: KeyLike) -> Scope:
        """Return subset of scope.

        :param scope: [opt] Scope to subset.
            If str, can be {'avail', 'loaded', 'selected', 'current'},
            corresponding scope of data will then be taken.
        :param keyring: [opt] Act on `scope`.
        :param keys: [opt]
        :param name: [opt] Name of new scope. If None will take
            name of input scope.
        :param int2list: If True, integer keys are turned to list.
            This avoids squeezing dimensions. Default to True.

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
                              int2list: bool = True, name: str = None,
                              by_day: bool = False,
                              **keys: KeyLikeValue) -> Scope:
        """Return subset of scope.

        Arguments work similarly as :func:`DataDisk.load_by_value
        <tomate.db_types.data_disk.DataDisk.load_by_value>`.

        See also
        --------
        get_subscope
        """
        scope = self.get_scope(scope)
        keyring = scope.get_keyring_by_index(by_day=by_day, **keys)
        return self.get_subscope(scope, keyring, int2list, name)

    def select(self, scope: Union[str, Scope] = 'current',
               keyring: Keyring = None, **keys: KeyLike):
        """Set selection scope.

        :param scope: [opt] Scope to select from.
            If str, can be {'avail', 'loaded', 'selected', 'current'},
            corresponding scope will then be taken. Default to current scope
            (loaded if data has been loaded, avail otherwise).
        :param keyring: [opt] Keyring specifying parts of dimensions to take.
            Act on the specified scope.
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

        Arguments work similarly as :func:`DataDisk.load_by_value
        <tomate.db_types.data_disk.DataDisk.load_by_value>`.

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
        self.selected = self.get_subscope_by_value(scope, int2list=False,
                                                   by_day=by_day,
                                                   name='selected', **keys)

    def add_to_selection(self, scope: Union[str, Scope] = 'avail',
                         keyring: Keyring = None, **keys: KeyLike):
        """Expand 'selected' scope.

        :param Scope: [opt] If nothing was selected before, select keys from
             this scope.
        :param keyring: [opt]
        :param keys: [opt] Keys act on the parent scope of selection.
        """
        scope = self.selected
        if scope.is_empty():
            self.select(scope, keyring=keyring, **keys)
        else:
            keyring = Keyring.get_default(keyring, **keys, dims=self.avail.dims)
            keyring.make_str_idx(**scope.parent_scope.dims)
            keyring.set_shape(scope.parent_scope.dims)
            keyring = keyring + scope.parent_keyring
            keyring.sort_keys()
            keyring.simplify()
            self.select(scope=scope.parent_scope, keyring=keyring)

    def slice_data(self, keyring: Keyring = None, **keys: KeyLike):
        """Slice loaded data.

        :param keys: Keys act on loaded scope.
        """
        self.check_loaded()
        self.loaded.slice(keyring=keyring, **keys)

        for var in self.variables.values():
            if var.name not in self.loaded:
                var.unload()
            else:
                var.data = var.view(keyring=keyring, **keys)

    def unload(self):
        """Remove all data."""
        self.loaded.empty()
        for var in self.variables.values():
            var.unload()

    def set_data(self, variable: str, data: Array,
                 keyring: Keyring = None, **keys: KeyLike):
        """Set the data for a single variable.

        Wrapper around :func:`Variable.set_data
        <tomate.variable_base.Variable.set_data>`.

        :raises KeyError: If the variable was not created.
        """
        if variable not in self.avail or variable not in self.variables:
            raise KeyError(f"{variable} was not created. Use add_variable")
        self.variables[variable].set_data(data, keyring, **keys)

    def add_variable(self, variable: str, dims: List[str] = None,
                     var_class: Type = None, datatype: Any = None,
                     attrs: Dict[str, any] = None) -> Variable:
        """Add a new variable.

        Create variable object, and add variable to available scope.

        If `dims`, `var_class`, or `datatype` are not specified,
        the value in the VI for the pair `variable` / `_dims`,
        `_var_class`, `_datatype` are used, if not in the VI, the
        value in the VI without the leading underscores, and if not
        in the VI either, the default will be used (see below).

        :param variable: Name of variable
        :param dims: [opt] List of dimensions this variable vary along.
            If not specified or in VI, Tomate will try to guess
            from information in Filegroups.
            If it can't, defaults to all coordinates available.
        :param var_class: [opt] Variable subclass to use.
            Default to :class:`Variable<variables.base.Variable>`.
        :param datatype: [opt] Datatype for the array.
            Default to None.
        :param attrs: [opt] Attributes to put in the VI.
        """
        if variable in self.variables:
            log.warning('%s already in variables, it will be overwritten.')

        if dims is None:
            dims = self.vi.get_attribute_param(variable, 'dims', None)
        if dims is None:
            if hasattr(self, 'var_disk') and variable in self.var_disk:
                dims = guess_dimensions(self, variable)
        if dims is None:
            dims = self.coords

        if var_class is None:
            var_class = self.vi.get_attribute_param(variable, 'var_class', Variable)
        if var_class is None:
            var_class = self.vi.get_attribute_param('_all', 'var_class', Variable)

        if attrs is not None:
            self.vi.set_attributes(variable, **attrs)

        db_var = var_class(variable, dims, self)

        if variable not in self.avail:
            self.avail.var.append(variable)

        if datatype is None:
            datatype = self.vi.get_attribute_param(variable, 'datatype', None)
        if datatype is None:
            datatype = self.vi.get_attribute_param('_all', 'datatype', None)
        db_var.datatype = datatype

        self.variables[variable] = db_var
        return db_var

    def create_variables(self, disk=False, replace=False):
        """Create variables objects."""
        for var in self.avail['var']:
            if disk:
                self.var_disk.add(var)
            if var not in self.variables or replace:
                self.add_variable(var)

    def remove_loaded_variables(self, variables: Union[str, List[str]]):
        """Remove variables from loaded scope."""
        if isinstance(variables, str):
            variables = [variables]
        keep = [v for v in self.loaded if v not in variables]
        self.slice_data(var=keep)


def guess_dimensions(db: 'DataDisk', var: str):
    """Guess variables dimensions from filegroups."""

    try:
        krg = Keyring(var=var)
        krg.make_str_idx(var=db.avail.var)
        dims_fg = []
        for fg in db.filegroups:
            cmd = fg.get_fg_keyrings(krg)
            if cmd is not None:
                key = cmd.infile['var']
                key.make_list_int()
                dims = key.apply(fg.cs['var'].dimensions)
                dims = [d for d in dims if d in db.dims]
                dims_fg.append(dims)
    except Exception:
        return None

    if len(dims_fg) > 0:
        lengths = [len(z) for z in dims_fg]
        dims = list(dims_fg[lengths.index(max(lengths))])
    else:
        return None

    log.debug('Guessed dimensions %s for variable %s', dims, var)

    warn = False
    for d in db.coords:
        if d not in dims:
            for fg in db.filegroups:
                if fg.cs[d].shared:
                    warn = True

    if warn:
        log.warning(("'%s' dimension is shared, but not in guess (%s), "
                     "something might be wrong"), d, dims)

    return dims
