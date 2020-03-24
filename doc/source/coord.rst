
.. currentmodule :: data_loader.coordinates


Coordinates
===========

Each dimension of the data is associated with a coordinate, stored as a
:class:`Coord<coord.Coord>` object.
This object stores the values of the coordinate, its size, and a few other
informations.
The values of the coordinate must be strictly monotonous. They can be
descending, though this is not currently supported everywhere in the package,
and should be avoided as of now.

Each coordinate can have a units attribute (only cosmetic).
It can also contain a `name_alt` attribute, a list of strings that list the
possible names this coordinate/dimension can be found in the files. For
instance, the latitude coordinate can be found under either `lat` or `latitude`.

The coordinate contains various methods to find the index of a value.
For instance, :func:`get_index<coord.Coord.get_index>` to find
the index of the element in the coordinate closest to a value.
The closest above, below, or closest of both can be picked.
The :func:`subset<coord.Coord.subset>` function is also
very useful, it returns the slice that will select indices between
a min and max value. For instance::

  slice_lat = lat.subset(10, 20)


Variables
---------

The variables available constitute a dimension of the data.
In most of the package, the 'dimensions' will design the variables
and coordinates dimensions, but 'coordinates' will exclude variables.

In the inner workings of the package, variable are just a specific
type of coordinate that support having string of characters as values
(among other things). Most of the user API supports refering to variables
by both their index in the coordinate object, and their name.
See :class:`variables.Variables`.
Note to developpers: they are some things to consider when using
keys and keyring for variables, see
FIXME:

**The variable coordinate is always named 'var'.**
This is the name it can be found in scopes, keyrings, and the name
that should be used in methods arguments.

In the Variables object, variables are stored in the order corresponding
to the scope (for example, for the loaded scope, it will correspond to the
order of the variable in the array).
One can easily retrieve the index of one or more variables using the
:func:`idx<variables.Variables.idx>`,
:func:`get_index<variables.Variables.get_index>`, or
:func:`get_indices<variables.Variables.get_indices>`
methods.


Some examples of coordinates subclasses
---------------------------------------

Time
++++

The :class:`Time<time.Time>` class has a few additional
functionnalities to treat date values more easily.
Most notably one can obtain dates from index, or vice-versa using
Time.index2date() and Time.date2index().

The units is here mandatory, and must comply to CF metadata conventions, and
be of the form `<time units> since <reference time>`.
This functionality uses the intern datetime.datetime objects and third party
netCDF4.num2date and netCDF4.date2num functions.


Latitude and Longitude
++++++++++++++++++++++

Two classes :class:`Lat<latlon.Lat>` and :class:`Lon<latlon.Lon>` have specific
methods, mainly for formatting purposes.
