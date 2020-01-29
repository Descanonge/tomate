"""Coordinate class with additional features for date manipulation.

Use user settings to set locales.
"""

import locale
from typing import List

from datetime import datetime

from netCDF4 import date2num, num2date

from data_loader.coordinates.coord import Coord


locale.setlocale(locale.LC_ALL, '')


class Time(Coord):
    """Time coordinate.

    Values are stored as floats, and can be converted
    to datetime objects.

    Use user settings to set locales.

    Attributes
    ----------
    units: str
        Time units.
    """

    def get_extent_str(self) -> str:
        """Return extent as str."""
        return "%s - %s" % tuple(self.format(v)
                                 for v in self.index2date([0, -1]))

    def update_values(self, values: List[float]):
        """Update values.

        Raises
        ------
        ValueError
            If the coordinate has no units.
        """
        if self.units == "":
            raise ValueError("%s has no units" % self.name)

        super().update_values(values)

    def index2date(self, indices=None):
        """Return datetimes objects corresponding to indices.

        Parameters
        ----------
        indices: Slice, List[int], int

        Returns
        -------
        datetime.datetime or List[datetime]
        """
        if indices is None:
            indices = slice(None, None)

        dates = num2date(self[indices], self.units,
                         only_use_cftime_datetimes=False)

        # Sometimes, num2date returns a subclass of datetime
        # I convert it back to datetime.datetime
        # for i, d in enumerate(dates):
        #     if not isinstance(d, datetime):
        #         dates[i] = datetime(d.year, d.month, d.day,
        #                             d.hour, d.minute, d.second,
        #                             d.microsecond)

        return dates

    def date2index(self, dates):
        """Return indices corresponding to dates.

        Nearest index before date is chosen

        Parameters
        ----------
        dates: datetime.datetime or List[datetime] or List[int]
            Date or dates to find the index for.
            Dates are defined with datetime objects, or
            using a list of ints corresponding to
            ['year', 'month', 'day', 'hour', 'minute', 'second',
            'microsecond'].
        """
        # If the user has asked a single date
        single = False
        if isinstance(dates, datetime):
            single = True
            dates = [dates]

        elif all(isinstance(d, (int, float)) for d in dates):
            single = True
            dates = [datetime(*dates)]

        indices = []
        for date in dates:
            num = date2num(date, self.units)
            indices.append(self.get_index(num))

        if single:
            indices = indices[0]
        return indices

    def change_units(self, units: str):
        """Change time units.

        Parameters
        ----------
        units: str
            CF compliant time units.

        Examples
        --------
        >>> time.change_units("hours since 1950-01-01 12:00:00")
        """
        self._array = change_units(self._array, self.units, units)
        self.units = units

    @staticmethod
    def format(value, fmt=None):
        """Format value.

        Parameters
        ----------
        value: Float or datetime
        fmt: str
            Passed to string.format or datetime.strftime
        """
        if isinstance(value, datetime):
            if fmt is None:
                fmt = '%x %X'
            return value.strftime(fmt)
        if fmt is None:
            fmt = '{:.2f}'
        return fmt.format(value)

def change_units(values, units_old, units_new):
    """Change time units."""
    dates = num2date(values, units_old)
    values = date2num(dates, units_new)
    return values
