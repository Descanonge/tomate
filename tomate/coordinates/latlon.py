"""Latitude and Longitude support."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from tomate.coordinates.coord import Coord


class Lat(Coord):
    """Latitude coordinate.

    :param name: [opt] Identification of the coordinate.
    :param array: [opt] Values of the coordinate.
    :param units: [opt] Coordinate units
    :param fullname: [opt] Print name.
    """

    def __init__(self, name='lat', array=None,
                 units='degree_north', fullname='Latitude'):
        super().__init__(name, array, units, fullname)

    @staticmethod
    def format(value: float, fmt: str = '.2f') -> str:
        end = ['S', 'N'][value > 0]
        fmt = f'{{:{fmt}}}{end}'
        return fmt.format(abs(value))


class Lon(Coord):
    """Longitude coordinate.

    :param name: [opt] Identification of the coordinate.
    :param array: [opt] Values of the coordinate.
    :param units: [opt] Coordinate units
    :param fullname: [opt] Print name.
    """

    def __init__(self, name='lon', array=None,
                 units='degree_east', fullname='Longitude'):
        super().__init__(name, array, units, fullname)

    @staticmethod
    def format(value: float, fmt: str = '.2f') -> str:
        end = ['W', 'E'][value > 0]
        fmt = f'{{:{fmt}}}{end}'
        return fmt.format(abs(value))
