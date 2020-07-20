"""Coordinate which values are strings."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import Iterator, List, Optional, Sequence, Union

import numpy as np

from tomate.coordinates.coord import Coord
from tomate.custom_types import KeyLike, KeyLikeStr


class CoordStr(Coord):
    """Coordinate which values are strings."""

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
        s = [super().__str__()]
        if self.has_data():
            s.append(', '.join(self[:]))
        else:
            s.append("Empty")
        return '\n'.join(s)

    def get_extent_str(self, slc: KeyLike = None) -> str:
        if slc is None:
            slc = slice(None)
        return ', '.join(self[slc])

    def get_str_index(self, y: Union[str, int]) -> int:
        """Return index value.

        :param y: Name or index of value.
        """
        if isinstance(y, str):
            y = self.get_index(y)
        return y

    def get_index(self, value: str, loc: str = None) -> int:
        if value not in self._array:
            raise KeyError(f"'{value}' not in coordinate.")
        i = np.where(self._array == value)[0][0]
        i = int(i)
        return i

    def get_index_exact(self, value: str) -> Optional[int]:
        try:
            return self.get_index(value)
        except KeyError:
            return None

    def idx(self, y: Union[str, int]) -> int:
        """Return index of value."""
        return self.get_str_index(y)

    def get_str_name(self, y: Union[int, str]) -> str:
        """Return name of value.

        :param y: Index or name of value.
        """
        if isinstance(y, str):
            return y
        return self._array[y]

    def get_str_indices(self, y: KeyLikeStr) -> Union[int, List[int]]:
        """Returns indices of values.

        :param y: List of values names or indices,
            or slice (of integers or strings),
            or single values name or index.

        :returns: List of values indices, or a single
            value index.
        """
        if isinstance(y, (int, str)):
            return self.get_str_index(y)

        if isinstance(y, slice):
            start = self.get_str_index(y.start)
            stop = self.get_str_index(y.stop)
            y = slice(start, stop, y.step)
            y = list(range(*y.indices(self.size)))

        indices = [self.get_str_index(i) for i in y]
        return indices

    def get_str_names(self, y: KeyLikeStr) -> Union[str, List[str]]:
        """Return values names.

        :param y: List of values names or indices,
            or a single value name or index.
        """
        idx = self.get_str_indices(y)
        if isinstance(idx, int):
            return self._array[idx]
        names = [self._array[i] for i in idx]
        return names

    def __getitem__(self, y: KeyLikeStr) -> str:
        """Return value.

        :param y: Index or name of value(s).
        """
        indices = self.get_str_indices(y)
        return self._array[indices]

    def __iter__(self) -> Iterator[str]:
        return iter(self._array)

    def slice(self, key: KeyLikeStr = None):
        if key is None:
            key = slice(None)
        self.update_values(self[key])

    def append(self, var: str):
        """Add value."""
        variables = list(self[:]) + [var]
        self.update_values(variables)
