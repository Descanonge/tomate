"""Variable coordinate."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import Iterator, List, Optional, Sequence, Union

import numpy as np

from tomate.coordinates.coord import Coord
from tomate.custom_types import KeyLike, KeyLikeVar


class Variables(Coord):
    """List of variables.

    With easy access to their index in a potential
    array.
    Akin to a Coord object.

    Its name is always 'var'.

    :param array: [opt] Variables names.
    :param vi: [opt] VI containing information about those variables.
    :param kwargs: [opt] See Coord signature.
    """

    def __init__(self, array: Union[str, Sequence[str]] = None,
                 **kwargs):
        kwargs.pop('name', None)
        kwargs.pop('array', None)
        super().__init__('var', None, **kwargs)

        if array is not None:
            self.update_values(array, dtype=None)

    def update_values(self, values: Union[str, Sequence[str]], dtype=None):
        """Change variables names.

        :param values: New variables names.
        :param dtype: [opt] Dtype of the array.
            Default to a variation of np.U#.
        :type dtype: data-type
        """
        if isinstance(values, str):
            values = [values]
        self._array = np.array(values, dtype=dtype)
        self._size = self._array.size

    def __repr__(self):
        if self.has_data():
            s = "Variables: " + ', '.join(self[:])
        else:
            s = "No variables"
        return s

    def get_extent_str(self, slc: KeyLike = None) -> str:
        if slc is None:
            slc = slice(None)
        return ', '.join(self[slc])

    def get_var_index(self, y: Union[str, int]) -> int:
        """Return index of variable.

        :param y: Name or index of variable.
        """
        if isinstance(y, str):
            y = self.get_index(y)
        return y

    def get_index(self, value: str, loc: str = None) -> int:
        if value not in self._array:
            raise KeyError(f"'{value}' not in variables.")
        i = np.where(self._array == value)[0][0]
        i = int(i)
        return i

    def get_index_exact(self, value: str) -> Optional[int]:
        try:
            return self.get_index(value)
        except KeyError:
            return None

    def idx(self, y: Union[str, int]) -> int:
        """Return index of variable."""
        return self.get_var_index(y)

    def get_var_name(self, y: Union[int, str]) -> str:
        """Return name of variable.

        :param y: Index or name of variable.
        """
        if isinstance(y, str):
            return y
        return self._array[y]

    def get_var_indices(self, y: KeyLikeVar) -> Union[int, List[int]]:
        """Returns indices of variables.

        :param y: List of variables names or indices,
            or slice (of integers or strings),
            or single variable name or index.

        :returns: List of variable indices, or a single
            variable index.
        """
        if isinstance(y, (int, str)):
            return self.get_var_index(y)

        if isinstance(y, slice):
            start = self.get_var_index(y.start)
            stop = self.get_var_index(y.stop)
            y = slice(start, stop, y.step)
            y = list(range(*y.indices(self.size)))

        indices = [self.get_var_index(i) for i in y]
        return indices

    def get_var_names(self, y: KeyLikeVar) -> Union[str, List[str]]:
        """Return variables names.

        :param y: List of variables names or indices,
            or a single variable name or index.
        """
        idx = self.get_var_indices(y)
        if isinstance(idx, int):
            return self._array[idx]
        names = [self._array[i] for i in idx]
        return names

    def __getitem__(self, y: KeyLikeVar) -> str:
        """Return name of variable.

        :param y: Index or name of variable(s).
        """
        indices = self.get_var_indices(y)
        return self._array[indices]

    def __iter__(self) -> Iterator[str]:
        """Iter variables names."""
        return iter(self._array)

    def slice(self, key: KeyLikeVar = None):
        """Slice variables.

        :param key: Variables names or index (a key-like argument).
            Takes precedence over keyring.
        """
        if key is None:
            key = slice(None)
        self.update_values(self[key])

    def copy(self) -> "Variables":
        return Variables(self._array, units=self.units, fullname=self.fullname)

    def append(self, var: str):
        """Add variable."""
        variables = list(self[:]) + [var]
        self.update_values(variables)
