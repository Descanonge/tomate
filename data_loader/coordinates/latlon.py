"""Latitude and Longitude support."""

from data_loader.coordinates.coord import Coord

class Lat(Coord):

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
