"""User friendly way to input information."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import List, Union
from dataclasses import dataclass

from tomate.custom_types import KeyLikeStr
from tomate.coordinates.coord import Coord


@dataclass
class CoordScanSpec:
    """Specification for a scanning coordinate.

    :param coord: Parent coordinate object or name. Its name will be used to
        refer to the CoordScan object as well.
    :param shared: If is `'in'` or `True`, the CoordScan is 'in', if is
        `'shared'` or `False, the CoordScan` is 'shared', ie shared across
        multiple files. Defaults to 'in'.
    :param name: Name of the dimensions inside the files.
        If is None (default), the name of the coordinate is used.
    """
    coord: Union[str, Coord]
    shared: Union[str, bool] = 'in'
    name: str = None

    def process(self, dims: Union[Coord] = None):
        """Process arguments.

        Just apply directives as in class docstring.
        """
        if isinstance(self.shared, str):
            self.shared = {'in': False, 'shared': True}[self.shared]

        if isinstance(self.coord, str):
            try:
                self.coord = dims[self.coord]
            except KeyError:
                raise KeyError("'{}' is not in dimensions.".format(self.coord))
        if self.name is None:
            self.name = self.coord.name

    def __iter__(self):
        return iter([self.coord, self.shared, self.name])


class VariableSpec:
    """Specify elements for a scanning variable CoordScan.

    :param name: Name of the variable.
    :param in_idx: Name or index of the variable in file. If is
        `'__equal_as_name__'` (default), The variable name is used.
    :param dims: Dimensions along which the variable varies. Defaults to None.
    """
    def __init__(self, name: str,
                 in_idx: KeyLikeStr = '__equal_as_name__',
                 dims: List[str] = None):
        if in_idx == '__equal_as_name__':
            in_idx = name
        self.name = name
        self.in_idx = in_idx
        self.dims = dims
