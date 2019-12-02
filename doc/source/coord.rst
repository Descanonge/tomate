
Coordinates
===========

Each dimension of the data is associated with a coordinate, stored as a
:class:`Coord<data_loader.coord.Coord>` object.
This object stores the values of the coordinate, its size, and a few other
informations.
The values of the coordinate must be strictly monotonous. They can be
descending.

Each coordinate can have a unit attribute (only cosmetic).
It can also contain a `name_alt` attribute, a list of strings that list the
possible names this coordinate/dimension can be found in the files. For
instance, the latitude coordinate is generally called `lat` or `latitude`.

The coordinate contains various methods to find a values' index.

To scan files, this object (or any of its child class) is subclassed into a
:class:`CoordScan<data_loader.coord_scan.CoordScan>`, which has additional
functionnalities for scanning coordinate values.


Time
====

The :class:`Time<data_loader.time.Time>` class has a few additional
functionnalities to treat date values more easily.
Most notably one can obtain dates from index, or vice-versa using
Time.index2date() and Time.date2index().
The unit is here mandatory, and must comply to CF metadata conventions, and
be of the form `<time units> since <reference time>`.
This functionality uses the intern datetime.datetime objects and third party
netCDF4.num2date and netCDF4.date2num functions.
