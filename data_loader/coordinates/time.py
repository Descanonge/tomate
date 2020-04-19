"""Convenient management of dates.

Use user settings to set locales.
"""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


import locale
import logging

from datetime import datetime, timedelta

try:
    import netCDF4 as nc
except ImportError:
    _has_netcdf = False
else:
    _has_netcdf = True

from data_loader.coordinates.coord import Coord


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

    def get_extent_str(self, slc=None) -> str:
        """Return extent as str."""
        return "%s - %s" % tuple(self.format(v)
                                 for v in self.index2date(slc)[[0, -1]])

    def update_values(self, values, dtype=None):
        """Update values.

        Parameters
        ----------
        values: Sequence[Float]
            New values. Have matching time units of self.
        dtype: Numpy dtype
            Dtype of the array.
            Default to np.float64.

        See also
        --------
        Coord.update_values

        Raises
        ------
        ValueError
            If the coordinate has no units.
        """
        if self.units == "":
            raise ValueError("%s has no units" % self.name)

        super().update_values(values, dtype)

    def index2date(self, indices=None):
        """Return datetimes objects corresponding to indices.

        Parameters
        ----------
        indices: Slice, List[int], int, optional
            If None, all available are used.

        Returns
        -------
        datetime.datetime, List[datetime]
            Return a list if the input was a list.
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

    def date2index(self, dates):
        """Return indices corresponding to dates.

        Nearest index before date is chosen

        Parameters
        ----------
        dates: datetime.datetime, List[datetime], List[int]
            Date or dates to find the index for.
            Dates are defined with datetime objects, or
            using a list of ints corresponding to
            ['year', 'month', 'day', 'hour', 'minute', 'second',
            'microsecond'].

        Returns
        -------
        int, List[int]:
            Return a list if the input was a list.

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

    def get_index(self, value, loc='closest') -> int:
        """Return index of value.

        Parameters
        ----------
        value: Float, int, List, datetime
            Time value, can be timestamps corresponding to self units,
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

    def subset_day(self, dmin=None, dmax=None) -> slice:
        """Return slice between days dmin and dmax.

        Full day is selected (from 0am to 0pm).

        Parameters
        ----------
        dmin, dmax: float, datetime, List[int], optional
            Bounds days to select.
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
    def format(value, fmt=None) -> str:
        """Format value.

        Parameters
        ----------
        value: Float, datetime
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
    """Change time units.

    Parameters
    ----------
    values: Sequence[float]
        Current values.
    units_old: str
        Current units, in CF compliant format.
    units_new: str
        New units, in CF compliant format

    Returns
    -------
    Sequence[float]
        Values in new units.
    """
    if not _has_netcdf:
        raise ImportError("netCDF4 package necessary for change_units.")

    dates = nc.num2date(values, units_old)
    values = nc.date2num(dates, units_new)
    return values
