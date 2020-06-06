
.. toctree::
   :hidden:

.. currentmodule :: data_loader.coordinates


Coordinates
-----------

Each dimension of the data is associated with a coordinate, stored as a
:class:`Coord<coord.Coord>` object.
This object stores the values of the coordinate, its size, and a few other
informations.
The values of the coordinate must be strictly monotonous. They can be
descending, though this is not currently supported everywhere in the package,
and should be avoided as of now.

Each coordinate can have a units attribute (useful when scanning, see
:ref:`Units conversion`).

The coordinate contains various methods to find the index of a value.
For instance, :func:`get_index<coord.Coord.get_index>` to find
the index of the element in the coordinate closest to a value.
The closest above, below, or closest of both can be picked.
The :func:`subset<coord.Coord.subset>` function is also
very useful, it returns the slice that will select indices between
a min and max value. For instance::

  slice_lat = lat.subset(10, 20)


Variables
^^^^^^^^^

The list of variables available constitute a dimension of the data.
In the inner workings of the package, variables are just a specific
type of coordinate that support having string of characters as values
(among other things, see :class:`variables.Variables`).
It is often useful to treat variables and other coordinates separately,
so in the rest of the package, 'dimensions' (abbreviated dims) designate all
Coord objects including variables, but 'coordinates' (abbreviated coords) omit
the variables dimension.

**The variable coordinate will always be named 'var'.**
This is the name that can be found in scopes, keyrings, and the name
that should be used in methods arguments.
All alternative name can still be set to the scanning coordinate.

In the Variables object, variables are stored in order, reflecting for instance
the order of variable in the data array (for the loaded scope).
Most of the user API supports refering to variables
by both their index in the coordinate object, and their name.
One can easily retrieve the index of one or more variables using the
:func:`idx<variables.Variables.idx>`,
:func:`get_var_index<variables.Variables.get_var_index>`, or
:func:`get_var_indices<variables.Variables.get_var_indices>`
methods.


.. currentmodule :: data_loader

Note to developpers: they are some things to consider when using
keys and keyring for variables. Additional methods are provided to go
from index to variable name, and vice-versa (
:func:`keys.keyring.Keyring.make_idx_var`).
All methods for normal keys will work for keys defined from variables names,
except when using slices.
So::

  Keyring(var=slice('SST', 'SSH'))

is perfectly valid, but it is impossible without the Variables object
to find the list of variables this selects, whereas for indices we only need
the coordinate size (and we do not even need it in most cases, see
:func:`keys.key.guess_tolist` and
:func:`keys.key.guess_slice_shape`.
).
So these should be used with care, and one should not forget the user can
supply one of these !

.. currentmodule :: data_loader.coordinates


Some examples of coordinates subclasses
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Time
""""

The :class:`Time<time.Time>` class has a few additional
functionnalities to treat date values more easily.
Most notably one can obtain dates from index, or vice-versa using
Time.index2date() and Time.date2index().

The units is here mandatory, and must comply to CF metadata conventions, and
be of the form `<time units> since <reference time>`.
This functionality uses the intern datetime.datetime objects and third party
netCDF4.num2date and netCDF4.date2num functions.


Latitude and Longitude
""""""""""""""""""""""

Two classes :class:`Lat<latlon.Lat>` and :class:`Lon<latlon.Lon>` have specific
methods, mainly for formatting purposes.
