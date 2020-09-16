
.. toctree::
   :hidden:

.. currentmodule:: tomate.coordinates.coord


Coordinates
-----------

Each dimension of the data is associated with a coordinate, stored as a
:class:`Coord` object.
This object stores the values of the coordinate, its size, and a few other
informations.
The values of the coordinate are typically floats, but strings can also be
used (see :ref:`String coordinates and Variables`).
When using float, values must be strictly monotonous. They can be
descending, though this is not currently supported everywhere in the package,
and should be avoided as of now.

Each coordinate can have a units attribute (useful when scanning, see
:ref:`Units conversion`).

The coordinate contains various methods to find the index of a value.
For instance, :func:`get_index<Coord.get_index>` to find
the index of a coordinate point closest to a given value.
The closest above, below, or closest of both can be picked.
The :func:`subset<Coord.subset>` function is also
very useful, it returns the slice that will select indices between
a min and max value. For instance::

  slice_lat = lat.subset(10, 20)

:func:`get_index_exact<Coord.get_index_exact>` will return the index
of a value if it is present in the coordinate, or None otherwise.
One can search for multiple indices at once with :func:`get_indices
<Coord.get_indices>`.


.. currentmodule:: tomate.coordinates

String coordinates and Variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Coordinates objects were written with float values in mind, but
one can still use string as values using :class:`CoordStr<coord_str.CoordStr>`.
This is especially useful with variables, which are treated
as other coordinates, with :class:`Variables<variables.Variables>`, a
subclass of CoordStr.

.. note::

   The variable coordinate will always be named 'var'.
   This is the name that can be found in scopes, keyrings, and the name
   that should be used in methods arguments.

You may have noticed that I am happily mixing the terms 'dimensions' and
'coordinates'. The only exception is in some object containing coordinates
objects (most notably the Scopes). The attribute `'dims'` refers to all
coordinates objects, but `'coords'` omits the variable dimension.

The biggest difference with float coordinates is the management of
indices. The CoordStr object gains some methods to retrieve indices
from values (and vice-versa), see
:func:`get_str_index<coord_str.CoordStr.get_str_index>`, or
:func:`get_str_indices<coord_str.CoordStr.get_str_indices>`
As it is easy to go from value to index, Tomate handles the conversion
on its own. Other coordinates require the user to use a `*_by_value`
function or find the indices themself, whereas for string coordinates,
the user can simply supply a string or list of strings pretty much anywhere.

To developpers: the conversion index / value can be done in the keyring
using :func:`Keyring.make_str_idx<tomate.keys.keyring.Keyring.make_str_idx>`
and :func:`Keyring.make_idx_str<tomate.keys.keyring.Keyring.make_idx_str>`.
Both function should be supplied one or more string coordinates.


Some examples of coordinates subclasses
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. currentmodule:: tomate.coordinates.time

Time
""""

The :class:`Time` class has a few additional
functionnalities to treat date values more comfortably.

.. currentmodule:: tomate.coordinates.time.Time

One can obtain dates from indices using :func:`index2date()`.
Conversely, :func:`get_index` can receive a tuple of numbers that
will be interpreted as a date, subsequently all `*_by_value` functions can
also be fed a tuple of numbers (or a list of). I insist on *tuple*.

The Time class also has additional methods :func:`get_index_by_day`,
:func:`get_indices_by_day`, and :func:`subset_by_day`.
They are used in stead of their 'normal' counterparts when the argument
`'by_day'` is set to True in various functions of the package.
They allow to prioritize the date when finding indices.

- `get_index_by_day` and `get_indices_by_day` will restrict
  their search to the same day as the target.
  If there is no timestamp in the coordinate for the same day, it will
  complain and raise an error.

- `subset_by_day` works similarly as her sister `subset` but will completely
  include (or exclude if the keyword argument is specified) the days at the
  boundaries of the selection. If the day of one of the selection bounds is
  not present in the coordinate, the next (or previous) whole day is taken.

The units are here mandatory, and must comply to CF metadata conventions
(*ie* be of the form `<time units> since <reference time>`).
This class relies on the `cftime <https://github.com/Unidata/cftime>`__ package.
`cftime.datetime` objects are always used in favor of python built-in
'datetime'.

The Time coordinate also has a `calendar` attribute, again in line with CF
metadata convention and cftime calendar keyword. Default calendar is 'standard'.
Note as of now (2.1.0) this is not super heavily tested.


.. currentmodule:: tomate.coordinates.latlon


Latitude and Longitude
""""""""""""""""""""""

Two classes :class:`Lat` and :class:`Lon` have specific
methods, mainly for formatting purposes.
