"""Variable coordinate."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import Sequence, Union

from tomate.coordinates.coord_str import CoordStr


class Variables(CoordStr):
    """List of variables.

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

    def copy(self) -> 'Variables':
        return self.__class__(self._array, units=self.units, fullname=self.fullname)

    def get_index(self, value: str, loc: str = None) -> int:
        try:
            return super().get_index(value, loc)
        except KeyError:
            raise KeyError(f"'{value}' not in variables.")
