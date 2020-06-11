
.. toctree::
   :hidden:

.. currentmodule :: tomate.coordinates


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


.. currentmodule :: tomate

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

.. currentmodule :: tomate.coordinates


Some examples of coordinates subclasses
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. currentmodule:: tomate.coordinates.time

Time
""""

The :class:`Time` class has a few additional
functionnalities to treat date values more easily.

.. currentmodule:: tomate.coordinates.time.Time

One can obtain dates from indices using :func:`index2date()`.
:func:`get_index` and others can receive a tuple of numbers that will
be interpreted as a date.

The Time class also has additional methods :func:`get_index_by_day`,
:func:`get_indices_by_day`, and :func:`subset_by_day`.
They are used in stead of their 'normal' counterparts when the argument
`'by_day'` is set to True in various function of the package.
They allow to prioritize the date when finding indices.

- `get_index_by_day` and `get_indices_by_day` will restrict
  their search of indices to the same day as the target.
  If there is no timestamp in the coordinate for the same day, it will
  complain and raise an error.

- `subset_by_day` works similarly as her sister `subset` but will completely
  include (or exclude if the keyword argument is specified) the days at the
  boundaries of the selection. If the day of one of the selection bounds is
  not present in the coordinate, the next (or previous) whole day is taken.

The units is here mandatory, and must comply to CF metadata conventions
(*ie* be of the form `<time units> since <reference time>`).
This class relies on the `cftime <https://github.com/Unidata/cftime>`__ package.
`cftime.datetime` objects are always used in favor of python built-in 'datetime'.
This will allow to implement different calendars if needed.


.. currentmodule:: tomate.coordinates.latlon

Latitude and Longitude
""""""""""""""""""""""

Two classes :class:`Lat` and :class:`Lon` have specific
methods, mainly for formatting purposes.
