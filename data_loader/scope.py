"""Information on dimensions of data."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


from typing import Dict, Iterator, List, Sequence, Union

import numpy as np

from data_loader.custom_types import KeyLike, KeyLikeInt
from data_loader.keys.keyring import Keyring, Key
from data_loader.coordinates.coord import Coord
from data_loader.coordinates.time import Time
from data_loader.coordinates.variables import Variables


class Scope():
    """Information on data dimension.

    Holds list of variables, and coordinates.
    Give information on the scope shape and dimensions.

    Coordinates can be accessed as attributes:
    `Scope.name_of_coordinate`.
    Coordinates and variable list can be accessed as items:
    `Scope[{name of coordinate | 'var'}]`.

    Attributes
    ----------
    name: str
    coords: Dict[Coord]
        Coordinates present in the scope.
    parent_scope: Scope
        The parent scope if this object is a subpart of it.
    parent_keyring: Keyring
        The keyring used to get this scope.
    """

    def __init__(self, coords: List[Coord] = None,
                 name: str = None):
        coord_var = coords.pop('var', None).copy()
        if coord_var is None:
            coord_var = Variables([])
        self.var = coord_var

        if coords is None:
            coords = []

        self.coords = {c.name: c.copy() for c in coords}

        self.parent_scope = None
        self.parent_keyring = Keyring()
        self.reset_parent_keyring()
        self.name = name

    def reset_parent_keyring(self):
        """Reset parent keyring.

        Reset to taking everything in parent scope.
        """
        self.parent_keyring = Keyring(**{name: slice(None)
                                         for name in self.dims})
        self.parent_keyring.set_shape({name: c for name, c in self.dims.items()
                                       if c.size is not None and c.size > 0})

    def __str__(self):
        s = []
        if self.name is not None:
            s.append('name: %s' % self.name)
        for d in self.dims.values():
            if d.has_data() and d.size > 0:
                s += ['%s: %s, %s' % (d.name, d.get_extent_str(), d.size)]
            else:
                s += ['%s: Empty' % d.name]
        return '\n'.join(s)

    def __repr__(self):
        return '\n'.join([super().__repr__(), str(self)])

    def __getattribute__(self, attr):
        if attr in super().__getattribute__('coords'):
            return super().__getattribute__('coords')[attr]
        return super().__getattribute__(attr)

    def __getitem__(self, item: str) -> Coord:
        """Return list of var or coords.

        If item is 'var', return list of present variables.
        If item is a coordinate name, return coordinate.

        :raises KeyError: Dimension not in scope.
        """
        if item == 'var':
            return self.var
        if item not in self.coords:
            raise KeyError("'%s' not in scope coordinates" % item)
        return self.coords[item]

    def __iter__(self) -> Iterator[str]:
        """List of available variables."""
        if self.is_empty():
            varlist = []
        else:
            varlist = list(self.var)
        return iter(varlist)

    @property
    def dims(self) -> Dict[str, Coord]:
        """Dictionnary of all dimensions.

        ie coordinates + variables.

        :returns: {dimension name: dimension}
        """
        out = {'var': self.var}
        for name, c in self.coords.items():
            out[name] = c
        return out

    def subset(self, coords: List[str]) -> Dict[str, Coord]:
        """Return coordinates objects.

        :param coords: Coordinates names.
        """
        return {c: self.coords[c] for c in coords}

    def idx(self, variables: Union[str, int]) -> int:
        """Get index of variables in the array.

        Wrapper around Variables.idx()
        """
        return self.var.idx(variables)

    @property
    def shape(self) -> List[int]:
        """Shape of data."""
        shape = [d.size for d in self.dims.values()]
        return shape

    def is_empty(self) -> bool:
        """Is empty."""
        empty = any((not d.has_data() or d.size == 0)
                    for d in self.dims.values())
        return empty

    def empty(self):
        """Empty scope.

        No variables.
        All coordinates have no data.
        """
        for c in self.dims.values():
            c.empty()

    def slice(self, keyring: Keyring = None,
              int2list: bool = True, **keys: KeyLike):
        """Slices coordinates and variables.

        If a parameter is None, no change is made for
        that parameter.

        :param keyring: [opt]
        :param int2list: Transform int keys into lists, too make
            sure the dimension is not squezed.
            Default is True.
        :param keys: [opt]
        """
        keyring = Keyring.get_default(keyring, **keys, variables=self.var)
        keyring.make_total()
        if int2list:
            keyring.make_int_list()
        for c, k in keyring.items_values():
            self[c].slice(k)

        self.parent_keyring *= keyring

    def copy(self) -> 'Scope':
        """Return a copy of self."""
        scope = Scope(self.coords.values(), self.name)
        scope.parent_scope = self.parent_scope
        scope.parent_keyring = self.parent_keyring.copy()
        return scope

    def iter_slices(self, coord: str, size: int = 12,
                    key: KeyLikeInt = None) -> List[KeyLikeInt]:
        """Iter through slices of a coordinate.

        The prescribed slice size is a maximum, the last
        slice can be smaller.

        :param coord: Coordinate to iterate along to.
        :param size: Size of the slices to take.
        :param key: Subpart of coordinate to iter through.
        """
        if key is None:
            key = slice(None)
        key = Key(key)

        c = self[coord]
        key.set_shape_coord(c)

        n_slices = int(np.ceil(key.shape / size))
        slices = []
        for i in range(n_slices):
            start = i*size
            stop = min((i+1)*size, key.shape)
            key_out = key * Key(slice(start, stop))
            slices.append(key_out.value)

        return slices

    def iter_slices_parent(self, coord: str, size: int = 12) -> List[KeyLikeInt]:
        """Iter through slices of parent scope.

        The coordinate of the parent scope is
        itered through. Pre-selection is made
        by parent keyring.

        :param coord: Coordinate to iterate along to.
        :param size: Size of the slices to take.

        See also
        --------
        iter_slices

        Examples
        --------
        We make a selection, and iterate through it.
        >>> dt.select(time=slice(10, 15))
        >>> for time_slice in dt.selected.iter_slices_parent('time', 3):
        ...     print(time_slice)
        slice(10, 12, 1)
        slice(12, 14, 1)
        [14]
        """
        if self.parent_scope is None:
            raise Exception("No parent scope.")
        key = self.parent_keyring[coord].value
        slices = self.parent_scope.iter_slices(coord, size, key)
        return slices

    def iter_slices_month(self, coord: str = 'time',
                          key: KeyLikeInt = None) -> List[KeyLikeInt]:
        """Iter through monthes of a time coordinate.

        :param coord: Coordinate to iterate along to.
            Must be subclass of Time.

        See also
        --------
        iter_slices: Iter through any coordinate
        """
        if key is None:
            key = slice(None)
        key = Key(key)

        c = self[coord]
        key.set_shape_coord(c)

        if not issubclass(type(c), Time):
            raise TypeError("'%s' is not a subclass of Time (is %s)"
                            % (coord, type(coord)))

        dates = c.index2date(key.value)
        slices = []
        indices = []
        m_old = dates[0].month
        y_old = dates[0].year
        for i, d in enumerate(dates):
            m = d.month
            y = d.year
            if m != m_old or y != y_old:
                key_out = key * Key(indices)
                key_out.simplify()
                slices.append(key_out.value)
                indices = []
            indices.append(i)
            m_old = m
            y_old = y
        slices.append(indices)

        return slices

    def get_limits(self, *coords: str,
                   keyring: Keyring = None,
                   **keys: KeyLikeInt) -> List[float]:
        """Return limits of coordinates.

        Min and max values for specified coordinates.
        Scope is loaded if not empty, available otherwise.

        :param coords: Coordinates name.
            If None, defaults to all coordinates, in the order
            of data.
        :param keyring: [opt] Subset coordinates.
        :param keys: [opt] Subset coordinates.
            Take precedence over keyring.

        :returns: Min and max of each coordinate. Flattened.
        """
        keyring = Keyring.get_default(keyring, **keys)
        keyring.make_full(coords)
        if not keyring:
            keyring.make_full(self.coords.keys())
        keyring.make_total()

        limits = []
        for name, key in keyring.items_values():
            limits += self[name].get_limits(key.no_int())
        return limits

    def get_extent(self, *coords: str,
                   keyring: Keyring = None,
                   **keys: KeyLikeInt) -> List[float]:
        """Return extent of loaded coordinates.

        Return first and last value of specified coordinates.

        :param coords: Coordinates name.
            If None, defaults to all coordinates, in the order
            of data.
        :param keyring: [opt] Subset coordinates.
        :param keys: [opt] Subset coordinates.
            Take precedence over keyring.

        :returns: First and last values of each coordinate.
        """
        keyring = Keyring.get_default(keyring, **keys)
        keyring.make_full(coords)
        if not keyring:
            keyring.make_full(self.coords.keys())
        keyring.make_total()

        extent = []
        for name, key in keyring.items_values():
            extent += self[name].get_extent(key)
        return extent
