
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
instance, the latitude coordinate can be found under either `lat` or `latitude`.

The coordinate contains various methods to find the index of a value.
For instance, :func:`get_index<data_loader.coord.Coord.get_index>` to find
the index of the element in the coordinate closest to a value.
The closest above, below, or closest of both can be picked.
The :func:`subset<data_loader.coord.Coord.subset>` function is also
very useful, it returns the slice that will select indices between
a min and max value (included). For instance::

  slice_lat = lat.subset(10, 20)


Time
----

The :class:`Time<data_loader.time.Time>` class has a few additional
functionnalities to treat date values more easily.
Most notably one can obtain dates from index, or vice-versa using
Time.index2date() and Time.date2index().

The unit is here mandatory, and must comply to CF metadata conventions, and
be of the form `<time units> since <reference time>`.
This functionality uses the intern datetime.datetime objects and third party
netCDF4.num2date and netCDF4.date2num functions.


CoordScan
---------

To scan files, each Coord (or any of its child class) is subclassed into a
:class:`CoordScan<data_loader.coord_scan.CoordScan>`, which has additional
functionnalities for scanning coordinate values.
The CoordScan class dynamically inherits from any subclass of Coord.
This demands that the class derived from Coord has the same arguments for its
creation.

More info on :doc:`scanning<scanning>`.
