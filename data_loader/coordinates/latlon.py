"""Latitude and Longitude support."""

from data_loader.coordinates.coord import Coord


class Lat(Coord):
    """Latitude coordinate."""

    def __init__(self, name='lat', array=None,
                 units='deg', fullname='Latitude', alt_name='latitude'):
        super().__init__(name, array, units, alt_name, fullname)

    @staticmethod
    def format(value, fmt='.2f'):
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
    """Longitude coordinate."""
    # TODO: convert to km

    def __init__(self, name='lon', array=None,
                 units='deg', fullname='Longitude', alt_name='longitude'):
        super().__init__(name, array, units, alt_name, fullname)


    @staticmethod
    def format(value, fmt='.2f'):
        """Format value.

        Parameters
        ----------
        value: float
        fmt: str
        """
        end = ['W', 'E'][value > 0]
        fmt = '{:%s}%s' % (fmt, end)
        return fmt.format(abs(value))
