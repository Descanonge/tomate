"""Latitude and Longitude support."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


from data_loader.coordinates.coord import Coord


class Lat(Coord):
    """Latitude coordinate.

    Parameters
    ----------
    name: str, optional
        Identification of the coordinate.
    array: Sequence, optional
        Values of the coordinate.
    units: str, optional
        Coordinate units
    fullname: str, optional
        Print name.
    """

    def __init__(self, name='lat', array=None,
                 units='deg', fullname='Latitude'):
        super().__init__(name, array, units, fullname)

    @staticmethod
    def format(value, fmt='.2f') -> str:
        """Format value.

        Parameters
        ----------
        value: float
        fmt: str
        """
        end = ['S', 'N'][value > 0]
        fmt = '{:%s}%s' % (fmt, end)
        return fmt.format(abs(value))


class Lon(Coord):
    """Longitude coordinate.

    Parameters
    ----------
    name: str, optional
        Identification of the coordinate.
    array: Sequence, optional
        Values of the coordinate.
    units: str, optional
        Coordinate units
    fullname: str, optional
        Print name.
    """
    # TODO: convert to km

    def __init__(self, name='lon', array=None,
                 units='deg', fullname='Longitude'):
        super().__init__(name, array, units, fullname)


    @staticmethod
    def format(value, fmt='.2f') -> str:
        """Format value.

        Parameters
        ----------
        value: float
        fmt: str
        """
        end = ['W', 'E'][value > 0]
        fmt = '{:%s}%s' % (fmt, end)
        return fmt.format(abs(value))
