"""Holds timestamps with additional functionalities.

Time class stores timestamps as tuple.
Also stores the unit, and methods using
datetime objects.

Use user settings to set locales.

Contains
--------
Time
    Time class

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

    Attributes
    ----------
    unit: str = "seconds since 1970-01-01 00:00:00"
        Time unit
    """

    def get_extent_str(self) -> str:
        """Return extent as str."""
        return "{0} - {1}".format(*[z.strftime("%x %X")
                                    for z in self.index2date([0, -1])])

    def update_values(self, values: List[float]):
        # TODO: raise if no unit ?
        if self.unit == "":
            self.unit = "seconds since 1970-01-01 00:00:00"

        super().update_values(values)

    def index2date(self, indices):
        """Return a list of datetime objects corresponding to indices.

        Parameters
        ----------
        indices: Slice, List of int, List of slice, int

        Returns
        -------
        List of datetime
        """
        if indices is None:
            indices = range(self.size)
        if isinstance(indices, slice):
            indices = list(range(*indices.indices(self.size)))
        if isinstance(indices, int):
            indices = [indices]
        dates = num2date([self[i] for i in indices], self.unit)

        for i in range(len(dates)):
            d = dates[i]
            if not isinstance(d, datetime):
                dates[i] = datetime(d.year, d.month, d.day,
                                    d.hour, d.minute, d.second,
                                    d.microsecond)
        return dates

    def date2index(self, dates: List[datetime]) -> List[int]:
        """Return a list of index corresponding to dates.

        Nearest index before date is chosen
        """
        indexes = []
        for date in dates:
            num = date2num(date, self.unit)
            indexes.append(self.get_index(num))
        return indexes

    def change_unit(self, unit: str):
        """Change time unit."""
        dates = num2date(self._array, self.unit)
        values = date2num(dates, unit)
        self._array = values
        self.unit = unit

    def get_collocated_times(self, time2: "Time") -> List[List[int]]:
        # REVIEW: collocated times
        """Find dates found both in instance and time2.

        Return lists for time1 and time2
        """

        l1 = []
        l2 = []
        for i1, t1 in enumerate(self._array):
            try:
                i2 = time2[:].index(t1)
            except ValueError:
                pass
            else:
                l1.append(i1)
                l2.append(i2)

        return l1, l2
