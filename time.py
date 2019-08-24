"""Holds timestamps with additional functionalities.

Time class stores timestamps as tuple.
Also stores the units, and methods using
datetime objects.
"""

from netCDF4 import date2num, num2date
from datetime import datetime

from myPack.analysis import get_closest


class Time(tuple):
    """Stores timestamps like tuple and the units as attribute.

    Can be sliced, then return a smaller Time instance.
    """

    def __new__(self, time, units):
        """."""
        return super().__new__(self, time)

    def __init__(self, time, units):
        self.units = units

    def __getitem__(self, key):
        """Return timestamp or time subset.

        If sliced returns another time element with the same units.
        """
        try:
            return Time(super().__getitem__(key), self.units)
        except TypeError:
            return super().__getitem__(key)

    def index2date(self, indices=None):
        """Return a list of datetime objects corresponding to indices."""
        if indices is None:
            indices = range(len(self))
        if isinstance(indices, slice):
            indices = list(range(*indices.indices(len(self))))
        dates = num2date([self[i] for i in indices], self.units)

        for i in range(len(dates)):
            d = dates[i]
            if type(d) != datetime:
                dates[i] = datetime(d.year, d.month, d.day,
                                    d.hour, d.minute, d.second,
                                    d.microsecond)
        return dates

    def date2index(self, dates):
        """Return a list of index corresponding to dates.

        Nearest index before date is chosen
        """

        indexes = []
        for date in dates:
            num = date2num(date, self.units)
            indexes.append(get_closest(self, num))
        return indexes


def get_collocated_times(time1, time2):
    """Find dates found both in time1 and time2.

    Return lists for time1 and time2
    """

    l1 = []
    l2 = []
    for i1, t1 in enumerate(time1):
        try:
            i2 = time2.index(t1)
        except ValueError:
            pass
        else:
            l1.append(i1)
            l2.append(i2)

    return l1, l2
