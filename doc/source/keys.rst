
Keys: Accessing data
====================

Keyrings
--------

In multiple places of the package, data has to be selected according
to indices of the data coordinates (ie dimensions).
A selection along a coordinate is done using a 'key'. It can be an integer,
a list of integer, or a slice.
Multiple keys are regrouped into a single object: a
:class:`Keyring<data_loader.Keyring>`.
This object is similar to a dictionnary. The keys are stored in a
:class:`Key<data_loader.key.Key>` class.
In the rest of the documentation a key designates either a Key object, or the
actual variable the user is demanding.
A 'key-like object', or a 'key value' designates unambiguously the latter.

A keyring provides many useful functions to manipulate the indices a user
is demanding, as well as different attributes and methods to iterate through
coordinates, keys, key-like values.
A lot of function still take a serie of key-like keyword argument, the easiest
way to convert a keyring to keywords arguments is::

  some_function(**keyring.kw)

Developpers are invited to look at the API doc-strings for further information.


Accessing arrays
----------------

Data is stored (and typically found) in numpy arrays.
The package allows for indexing the array ways that are slightly out
of the normal use of numpy indexing.

Namely, asking for lists of indices for different dimensions is
not straightforward in python. For instance we could think that::

  data[[0, 1], [10, 11, 12], :]

would take the first two indices of the time coordinate,
and the indices [10, 11, 12] for the latitude.
However this won't work (see numpy doc page on indexing for more details).

The package provides functions to access arrays that are available in the
keyring object.

First if there is no particular issue with normal indexing.
The keys values are then appended into a tuple and passed to the array
(see :func:`get_array_simple<data_loader.Keyring.get_array_normal>`
and :func:`place_simple<data_loader.Keyring.place_normal>`).

Secondly if there is an issue with normal indexing such that more complicated
means are necessary.
This is the case if there is any combination of integer keys and list keys,
or more than one list keys.

In the complex case, multiple successive access to the array are made,
so `array[0, [0, 1, 2], :, [1]]` is transformed into
`array[0][[0, 1, 2]][:, :][:, :, [1]]`.
To write data, a loop is done.
(see :func:`get_array_complex<data_loader.Keyring.get_array_complex>`
and :func:`place_complex<data_loader.Keyring.place_complex>`)

Examples::

  # Normal indexing
  time=0, lat=2, lon=5
  time=0, lat=slice(None, None), lon=5
  time=[0, 1], lat=slice(None, None), lon=slice(None, None)

  # Complex indexing
  time=0, lat=[1], lon=5
  time=[0, 1], lat=[0, 1, 3, 5], lon=slice(None, None)
  time=[0], lat=[15], lon=[1, 2, 3]

It is important to note that in that case, the returned array will be a copy
and not a view of the original index.
To mitigate this issue, keys are converted to slices whenever possible, as
they are easy to manipulate and do not pose any array access problems.


Integers vs lists
-----------------

As with numpy normal indexing, an integer key will result in the dimension
being squeezed, but a list of length one (or the corresponding slice) will
keep the dimension.
The expection to this rule is when using
:func:`load_data<data_loader.DataBase.load_data>` and
:func:`slice_data<data_loader.DataBase.slice_data>` (or other functions
acting on the data). The Data object will always keep the same number of
dimensions (ie the number of coordinates).
