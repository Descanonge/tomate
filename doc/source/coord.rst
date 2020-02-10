
.. currentmodule :: data_loader


Coordinates
===========

Each dimension of the data is associated with a coordinate, stored as a
:class:`Coord<coordinates.coord.Coord>` object.
This object stores the values of the coordinate, its size, and a few other
informations.
The values of the coordinate must be strictly monotonous. They can be
descending.

Each coordinate can have a units attribute (only cosmetic).
It can also contain a `name_alt` attribute, a list of strings that list the
possible names this coordinate/dimension can be found in the files. For
instance, the latitude coordinate can be found under either `lat` or `latitude`.

The coordinate contains various methods to find the index of a value.
For instance, :func:`get_index<coordinates.coord.Coord.get_index>` to find
the index of the element in the coordinate closest to a value.
The closest above, below, or closest of both can be picked.
The :func:`subset<coordinates.coord.Coord.subset>` function is also
very useful, it returns the slice that will select indices between
a min and max value. For instance::

  slice_lat = lat.subset(10, 20)


Time
----

The :class:`Time<coordinates.time.Time>` class has a few additional
functionnalities to treat date values more easily.
Most notably one can obtain dates from index, or vice-versa using
Time.index2date() and Time.date2index().

The units is here mandatory, and must comply to CF metadata conventions, and
be of the form `<time units> since <reference time>`.
This functionality uses the intern datetime.datetime objects and third party
netCDF4.num2date and netCDF4.date2num functions.

