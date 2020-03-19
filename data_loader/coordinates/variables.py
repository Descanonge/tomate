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

    Its name is always 'var'.

    Parameters
    ----------
    array: Sequence[str], optional
        Variables names.
    vi: VariablesInfo, optional
        VI containing information about those variables.
    kwargs:
        See Coord signature.

    Attributes
    ----------
    vi: VariablesInfo
        VI containing information about variables.
    """

    def __init__(self, array=None, vi=None, **kwargs):
        kwargs.pop('name', None)
        kwargs.pop('array', None)
        super().__init__('var', None, **kwargs)

        if array is not None:
            self.update_values(array, dtype=None)

        self.vi = vi

    def update_values(self, values, dtype=None):
        """Change variables names.

        Parameters
        ----------
        values: Sequence[str], str
            New variables names.
        dtype: Numpy dtype
            Dtype of the array.
            Default to a variation of np.U#.
        """
        if isinstance(values, str):
            values = [values]
        self._array = np.array(values, dtype=dtype)
        self._size = self._array.size

    def __str__(self):
        s = "Variables: " + ', '.join(self[:])
        return s

    def idx(self, y) -> int:
        """Return index of variable.

        Parameters
        ----------
        y: str, int
            Name or index of variable.
        """
        if isinstance(y, str):
            y = np.where(self._array == y)[0][0]
            y = int(y)
        return y

    def get_index(self, value, loc=None) -> int:
        return self.idx(value)

    def get_name(self, y) -> str:
        """Return name of variable.

        Parameters
        ----------
        y: int, str
            Index or name of variable.
        """
        if isinstance(y, str):
            return y
        return self._array[y]

    def get_indices(self, y):
        if isinstance(y, (int, str)):
            return self.idx(y)

        if isinstance(y, slice):
            start = self.idx(y.start)
            stop = self.idx(y.stop)
            y = slice(start, stop, y.step)
            y = list(range(*y.indices(self.size)))

        out = [self.idx(i) for i in y]
        return out

    def get_names(self, y):
        idx = self.get_indices(y)
        if isinstance(idx, int):
            return self._array[idx]
        out = [self._array[i] for i in idx]
        return out

    def __getitem__(self, y) -> str:
        """Return name of variable.

        Parameters
        ----------
        y: int, str, List[int], List[str], slice
            Index or name of variable(s).
        """
        return self.get_names(y)

    def __iter__(self):
        """Iter variables names."""
        return iter(self._array)

    def slice(self, key=None):
        """Slice variables.

        Parameters
        ----------
        key: key-like
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

    def set_attr(self, name, attr):
        self.vi.add_attrs_per_variable(name, attr)
