"""Information on dimensions of data."""

import numpy as np

from data_loader.key import Keyring
from data_loader.iter_dict import IterDict
from data_loader.coordinates.time import Time


class Scope():
    """Information on data dimension.

    What variables, and what part of coordinates
    are in the scope.

    Parameters
    ----------
    coords: Coord

    Attributes
    ----------
    coords: Dict[Coord]
    var: List[str]
    """

    def __init__(self, variables=None, *coords):
        if variables is None:
            variables = []
        self.var = list(variables).copy()
        self.coords = {c.name: c.copy() for c in coords}

    def __str__(self):
        s = []
        if not self.is_empty():
            s += ['variables: %s' % self.var]
            s += ['%s: %s, %s' % (name, c.get_extent_str(), c.size)
                  for name, c in self.coords.items()]
        return '\n'.join(s)

    def __repr__(self):
        return '\n'.join([super().__repr__(), str(self)])

    def __getattribute__(self, attr):
        if attr in super().__getattribute__('coords'):
            return super().__getattribute__('coords')[attr]
        return super().__getattribute__(attr)

    def __getitem__(self, item):
        if item == 'var':
            return self.var
        if item not in self.coords:
            raise KeyError("'%s' not in scope coordinates" % item)
        return self.coords[item]

    def __iter__(self):
        return iter(self.coords.keys())

    def subset(self, coords):
        return {c: self.coords[c] for c in coords}

    @property
    def idx(self):
        """Index of variable in data array."""
        return IterDict(dict(zip(self.var, range(len(self.var)))))

    @property
    def shape(self):
        """Shape of data."""
        shape = [len(self.var)] + [c.size for c in self.coords.values()]
        return shape

    def is_empty(self):
        """Is empty."""
        return not self.var

    def empty(self):
        """Empty scope.

        No variables.
        All coordinates have no data.
        """
        self.var = []
        for c in self.coords.values():
            c.empty()

    def slice(self, **keys):
        """Slices coordinates and variables.

        Parameters
        ----------
        keys: Key-like
            Coordinates to slice, argument name is coordinate name.
            Variables can be sliced as well, by specifying
            a argument with name 'var', equal to a str or a List[str].
        """
        if 'var' in keys:
            key = keys['var']
            if key is None:
                key = self.var
            elif isinstance(key, str):
                key = [key]
            keys['var'] = list(key)

        for c, k in keys.items():
            if c == 'var':
                self.var = [v for v in k if v in self.var]
            else:
                self[c].slice(k)

    def copy(self):
        """Return a copy."""
        return self.__class__(self.var, *self.coords.values())

    def iter_slices(self, coord, size_slice=12):
        """Iter through data with slices of `coord` of size `n_iter`.

        Parameters
        ----------
        coord: str
            Coordinate to iterate along to.
        size_slice: int, optional
            Size of the slices to take.
        """
        c = self[coord]

        n_slices = int(np.ceil(c.size / size_slice))
        slices = []
        for i in range(n_slices):
            start = i*size_slice
            stop = min((i+1)*size_slice, c.size)
            slices.append(slice(start, stop))

        return slices

    def iter_slices_month(self, coord='time'):
        """Iter through data with slices corresponding to a month.

        Parameters
        ----------
        coord: str, optional
            Coordinate to iterate along to.
            Must be subclass of Time.

        Raises
        ------
        TypeError:
            If the coordinate is not a subclass of Time.

        See also
        --------
        iter_slices: Iter through any coordinate
        """
        c = self[coord]
        if not issubclass(type(c), Time):
            raise TypeError("'%s' is not a subclass of Time (is %s)"
                            % (coord, type(coord)))

        dates = c.index2date()
        slices = []
        indices = []
        m_old = dates[0].month
        y_old = dates[0].year
        for i, d in enumerate(dates):
            m = d.month
            y = d.year
            if m != m_old or y != y_old:
                slices.append(indices)
                indices = []
            indices.append(i)
            m_old = m
            y_old = y
        slices.append(indices)

        return slices

    def get_limits(self, *coords, **kw_keys):
        """Return limits of coordinates.

        Min and max values for specified coordinates.

        Parameters
        ----------
        coords: List[str]
            Coordinates name.
            If None, defaults to all coordinates, in the order
            of scope.
        kw_keys: Any
            Subset of coordinates

        Returns
        -------
        limits: List[float]
            Min and max of each coordinate. Flattened.
        """
        kw_keys.update({name: None for name in coords})
        if not kw_keys:
            kw_keys = {name: None for name in self.coords_name}
        keyring = Keyring(**kw_keys)
        keyring.make_total()

        limits = []
        for name, key in keyring.items_values():
            limits += self[name].get_limits(key)
        return limits

    def get_extent(self, *coords, **kw_keys):
        """Return extent of coordinates.

        Return first and last value of specified coordinates.

        Parameters
        ----------
        coords: List[str]
            Coordinates name.
            If None, defaults to all coordinates, in the order
            of scope.
        kw_coords: Any
            Subset of coordinates

        Returns
        -------
        limits: List[float]
            First and last values of each coordinate.
        """
        kw_keys.update({name: None for name in coords})
        if not kw_keys:
            kw_keys = {name: None for name in self.coords_name}
        keyring = Keyring(**kw_keys)
        keyring.make_total()

        extent = []
        for name, key in keyring.items_values():
            extent += self[name].get_extent(key)
        return extent
