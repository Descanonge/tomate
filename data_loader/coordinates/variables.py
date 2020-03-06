"""Variable coordinate."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


import numpy as np
from data_loader.coordinates.coord import Coord


class Variables(Coord):
    """List of variables.

    With easy access to their index in a potential
    array.
    Akin to a Coord coordinate object.

    Parameters
    ----------
    variables: str, List[str], optional
    """

    def __init__(self, array=None, **kwargs):
        kwargs.pop('name', None)
        kwargs.pop('array', None)
        super().__init__('var', None, **kwargs)

        if array is not None:
            self.update_values(array, dtype=None)

    def update_values(self, values, dtype=None):
        if isinstance(values, str):
            values = [values]
        self._array = np.array(values, dtype=dtype)
        self._size = self._array.size

    def __str__(self):
        s = "Variables: " + ', '.join([v for v in self])
        return s

    def idx(self, y):
        """Return index of variable.

        Parameters
        ----------
        y: str, int
            Name or index of variable.
        """
        if isinstance(y, str):
            y = np.where(self._array == y)[0][0]
        return y

    def get_index(self, value, loc=None):
        return self.idx(value)

    def get_name(self, y):
        """Return name of variable.

        Parameters
        ----------
        y: int, str
            Index or name of variable.
        """
        if isinstance(y, str):
            return y
        return self._array[y]

    def __getitem__(self, y):
        """Return name of variable.

        Parameters
        ----------
        y: int, str, List[int], List[str], slice
            Index or name of variable(s).
        """
        if isinstance(y, (int, str)):
            return self._array[self.idx(y)]

        if isinstance(y, slice):
            start = self.idx(y.start)
            stop = self.idx(y.stop)
            y = slice(start, stop, y.step)
            y = list(range(*y.indices(self.size)))

        out = [self._array[self.idx(i)] for i in y]
        return out

    def __iter__(self):
        """Iter variables names."""
        return iter(self._array)

    def slice(self, key=None):
        """Slice variables.

        Keep only variables overlaping with arguments.

        Parameters
        ----------
        keyring: Keyring
            The key must be named 'var'.
        variables: int, str, List[int], List[str]
            Variables names or index (a key-like argument).
            Takes precedence over keyring.
        """
        if key is None:
            key = slice(None)
        self.update_values(self[key])

    def copy(self):
        """Return a copy."""
        return Variables(self[:], units=self.units, name_alt=self.name_alt,
                         fullname=self.fullname)
