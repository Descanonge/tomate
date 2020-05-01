"""Convenient management of dates.

Use user settings to set locales.
"""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


import locale
import logging
from typing import List, Sequence, Union

from datetime import datetime, timedelta

try:
    import netCDF4 as nc
except ImportError:
    _has_netcdf = False
else:
    _has_netcdf = True

from data_loader.coordinates.coord import Coord
from data_loader.custom_types import KeyLike


log = logging.getLogger(__name__)
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


    def get_extent_str(self, slc: KeyLike = None) -> str:
        return "%s - %s" % tuple(self.format(v)
                                 for v in self.index2date(slc)[[0, -1]])

    def update_values(self, values: Sequence[float], dtype=None):
        """Update values.

        :param values: New values. Have matching time units of self.
        :param dtype: [opt] Dtype of the array.
            Default to np.float64.
        :type dtype: data-type

        :raises ValueError: If the coordinate has no units.

        See also
        --------
        data_loader.coordinates.coord.Coord.update_values
        """
        if self.units == "":
            raise ValueError("%s has no units" % self.name)

        super().update_values(values, dtype)

    def index2date(self, indices: KeyLike = None) -> Union[datetime,
                                                           List[datetime]]:
        """Return datetimes objects corresponding to indices.

        :param indices: [opt] If None, all available are used.
        :returns: Return a list if the input was a list.
        :raises ImportError: If netCDF4 package is missing.
        """
        if not _has_netcdf:
            raise ImportError("netCDF4 package necessary for index2date.")

        if indices is None:
            indices = slice(None, None)

        dates = nc.num2date(self[indices], self.units,
                            only_use_cftime_datetimes=False)

        # Sometimes, num2date returns a subclass of datetime
        # I convert it back to datetime.datetime
        # for i, d in enumerate(dates):
        #     if not isinstance(d, datetime):
        #         dates[i] = datetime(d.year, d.month, d.day,
        #                             d.hour, d.minute, d.second,
        #                             d.microsecond)

        return dates

    def date2index(self, dates) -> Union[int, List[int]]:
        """Return indices corresponding to dates.

        Nearest index before date is chosen

        :param dates: Date or dates to find the index for.
            Dates are defined with datetime objects, or
            using a list of ints corresponding to
            ['year', 'month', 'day', 'hour', 'minute', 'second',
            'microsecond'].
        :type dates: datetime.datetime, List[datetime], List[int]

        :returns: Return a list if the input was a list.

        .. deprecated: 0.4.0
            Is replaced by Time.get_indices().
        """
        log.warning("date2index() is deprecated. Use get_indices().")
        if not _has_netcdf:
            raise ImportError("netCDF4 package necessary for date2index.")

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
            num = nc.date2num(date, self.units)
            indices.append(self.get_index(num))

        if single:
            indices = indices[0]
        return indices

    @staticmethod
    def change_units_other(values: Sequence[float], old: str, new: str):
        """Change time units.

        CF compliant time units.

        Examples
        --------
        >>> time.change_units("hours since 1950-01-01 12:00:00")
        """
        if not _has_netcdf:
            raise ImportError("netCDF4 package necessary for change_units.")
        dates = nc.num2date(values, old)
        values = nc.date2num(dates, new)
        return values

    def get_index(self, value: Union[datetime, List[Union[int, float]],
                                     float, int],
                  loc: str = 'closest') -> int:
        """Return index of value.

        :param value: Time value, can be timestamps corresponding to self units,
            datetime object, or a list of value that can be transformed
            to date ([year, month, day [, hours, minutes, ...]])
        loc: {'closest', 'below', 'above'}
        """
        if isinstance(value, (list, tuple)):
            value = datetime(*value)
        if isinstance(value, datetime):
            if not _has_netcdf:
                raise ImportError("netCDF4 package necessary for get_index with dates.")
            value = nc.date2num(value, self.units)
        return super().get_index(value, loc)

    def subset_day(self, dmin: Union[datetime, List[int],
                                     float, int] = None,
                   dmax: Union[datetime, List[int],
                               float, int] = None) -> slice:
        """Return slice between days dmin and dmax.

        Full day is selected (from 0am to 0pm).

        :param dmin: Bounds days to select.
            If None, min and max of coordinate are taken.
        """
        if dmin is None:
            dmin = self.index2date(0)
        if dmax is None:
            dmax = self.index2date(-1)
        bounds = []
        for day in [dmin, dmax]:
            if isinstance(day, float):
                if not _has_netcdf:
                    raise ImportError("netCDF package necessary for subset_day with floats.")
                day = nc.num2date(day, self.units)
            elif isinstance(day, (list, tuple)):
                day = datetime(*day)

            bounds.append(day)

        tmin = datetime(bounds[0].year, bounds[0].month, bounds[0].day)
        tmax = datetime(bounds[1].year, bounds[1].month, bounds[1].day)
        day_min = tmin.date()
        day_max = tmax.date()
        tmax = tmax + timedelta(days=1)
        slc = self.subset(tmin, tmax)

        start, stop, step = slc.start, slc.stop, slc.step
        idx = list(range(*slc.indices(self.size)))
        i1, i2 = idx[0], idx[-1]

        if not self.is_descending():
            if self.index2date(i1).date() < day_min:
                start += 1
            if self.index2date(i2).date() > day_max:
                stop -= 1
        else:
            if self.index2date(i2).date() < day_min:
                stop -= 1
            if self.index2date(i1).date() > day_max:
                start += 1
        return slice(start, stop, step)

    @staticmethod
    def format(value: float, fmt: str = None) -> str:
        """Format value.

        :param fmt: Passed to string.format or datetime.strftime
        """
        if isinstance(value, datetime):
            if fmt is None:
                fmt = '%x %X'
            return value.strftime(fmt)
        if fmt is None:
            fmt = '{:.2f}'
        return fmt.format(value)
