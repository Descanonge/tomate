"""Coordinate class with additional features for date manipulation.

Use user settings to set locales.
"""

import locale
from typing import List

from datetime import datetime

from netCDF4 import date2num, num2date

from data_loader.coord import Coord


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
        return "{0} - {1}".format(*[z.strftime("%x %X")
                                    for z in self.index2date([0, -1])])

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
        indices: Slice, List[int], List[slice], int

        Returns
        -------
        datetime.datetime or List[datetime]
        """
        # If the user has asked an integer
        integer = False

        if indices is None:
            indices = range(self.size)
        if isinstance(indices, slice):
            indices = list(range(*indices.indices(self.size)))
        if isinstance(indices, int):
            integer = True
            indices = [indices]
        dates = num2date([self[i] for i in indices], self.units)

        # Sometimes, num2date returns a subclass of datetime
        # I convert it back to datetime.datetime
        for i, d in enumerate(dates):
            if not isinstance(d, datetime):
                dates[i] = datetime(d.year, d.month, d.day,
                                    d.hour, d.minute, d.second,
                                    d.microsecond)

        if integer:
            dates = dates[0]
        return dates

    def date2index(self, dates):
        """Return indices corresponding to dates.

        Nearest index before date is chosen

        Parameters
        ----------
        dates: datetime.datetime or List[datetime]
        """
        # If the user has asked a single date
        single = False
        if isinstance(dates, datetime):
            single = True
            dates = [dates]

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
        dates = num2date(self._array, self.units)
        values = date2num(dates, units)
        self._array = values
        self.units = units
