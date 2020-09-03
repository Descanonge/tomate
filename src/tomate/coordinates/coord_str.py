"""Coordinate with string values."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import Iterator, List, Optional, Sequence, Union

import numpy as np

from tomate.coordinates.coord import Coord
from tomate.custom_types import KeyLike


class CoordStr(Coord):
    """Coordinate with string values."""

    def update_values(self, values: Union[str, Sequence[str]], dtype=None):
        """Change values.

        :param values: New value(s).
        :param dtype: [opt] Dtype of the array.
            Default None, which gives a variation of np.U#.
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
        if isinstance(y, int):
            return y
        return self.get_index(y)

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

    def get_str_name(self, y: Union[int, str]) -> str:
        """Return name of value.

        :param y: Index or name of value.
        """
        if isinstance(y, str):
            return y
        return self._array[y]

    def get_str_indices(self, y: KeyLike) -> Union[int, List[int]]:
        """Returns indices of values.

        :returns: List of values indices, or a single value index,
            depending on key size.
        """
        if isinstance(y, (int, str)):
            return self.get_str_index(y)

        if isinstance(y, slice):
            start, stop = y.start, y.stop
            if isinstance(start, str):
                start = self.get_str_index(start)
            if isinstance(stop, str):
                stop = self.get_str_index(stop)
            y = slice(start, stop, y.step)
            y = list(range(*y.indices(self.size)))

        indices = [self.get_str_index(i) for i in y]
        return indices

    def get_str_names(self, y: KeyLike) -> Union[str, List[str]]:
        """Return values names.

        :returns: List of values, or a single value, depending
            on key size.
        """
        idx = self.get_str_indices(y)
        if isinstance(idx, int):
            return self._array[idx]
        names = [self._array[i] for i in idx]
        return names

    def __getitem__(self, y: KeyLike) -> str:
        """Return value.

        :param y: Index or name of value(s).
        """
        indices = self.get_str_indices(y)
        return self._array[indices]

    def __iter__(self) -> Iterator[str]:
        if self.has_data():
            var = self._array
        else:
            var = []
        return iter(var)

    def append(self, var: str):
        """Add value."""
        values = list(self[:]) + [var]
        self.update_values(values)

    def remove(self, var: str):
        """Remove value."""
        values = list(self[:])
        values.remove(var)
        self.update_values(values)

    @staticmethod
    def format(value: str, fmt: str = '{:s}') -> str:
        return fmt.format(value)
