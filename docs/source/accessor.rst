
.. currentmodule :: tomate.keys

Accessing data
==============

The package provides some low-level functions to access the data (loaded or on
disk), in a controlled fashion. This create an abstraction level, and allows to
change the implementation of how the data is stored.
The data is of course still directely accessible.

This page describes the API for accessing data this way. This is mostly
intended for developpers and my future self that will have forgotten everything,
the fool.


Selecting parts of arrays
-------------------------

It is often needed to select data in an array by index.
A selection along a dimension (or any other iterable) is done using a 'key'. It
can be an integer, a list of integers, or a slice.

As stated in :ref:`String coordinates and Variables`, Tomate expects the user
to input integer indices in most places. The exception to that are the plotting
function, functions ending in `*_by_value`, and when specifying keys for
string coordinates, in which cases Tomate will handle the conversion.

If this is still confusing, all methods needing keys as arguments have a
typehint that should clear it up, refer to :doc:`Custom types
<_references/tomate.custom_types>` for typehint details.


Keys and keyrings
+++++++++++++++++

Multiple keys are regrouped into a single object: a
:class:`Keyring<keyring.Keyring>`.
This object is similar to a dictionnary. The keys are stored in a
:class:`Key<key.Key>` class.
In the rest of the documentation a key designates either a Key object, or the
actual indices the user is demanding.
A 'key-like object', or a 'key value' designates unambiguously the latter.

Most functions take both a keyring and keyword arguments keys. The keyring
argument is here for internal use. Both arguments are merged, with keyword
arguments taking precedence.
The rest of this section is describing internal API that can be overlooked by
regular users.

A keyring provides many useful functions to manipulate the indices a user is
asking, as well as different attributes and methods to iterate through the
coordinates, keys, key-like values it contains.
Some functions in the package only take a serie of key-like keyword
arguments, the easiest way to convert a keyring to keywords arguments is::

  some_function(**keyring.kw)

Some functions can take both a keyring and keys in argument. The class function
:func:`keyring.Keyring.get_default` combines the two argument. It also make a
copy of the keyring, to avoid in-place modifications.

The size of a key designates the length a coordinate would have after the key
is applied. A shape 0 means it would return a scalar. None keys have a shape 0
as when taking data from file, a None in-file index means that dimension is
already squeezed.
Shape of slices keys will be infered if possible, but sometimes the shape of the
coordinate on which the slice will be applied is necessary. It is stored in the
:attr:`key.Key.parent_size` attribute once set.

The :attr:`keyring.Keyring.shape` property will return the shape of the array it
would give. Dimensions of size 0 are thus omitted. None indicates the shape of
that dimension is unknown.


String values keys
++++++++++++++++++

Coordinates with string values can be accessed using both index and variables
names. Both can be useful in different situations. In most cases though, the
user will be inputing variables names, and it is the method job to convert it
to an index if needed (whereas the user is expected to find the index for other
coordinates).

The subclass :class:`key.Key` supports both as well, it can consists of an
integer, a string, a list of integers or strings, or a slice of integer or
strings.
One can go from variable name to index (or vice-versa) using
:func:`keyring.Keyring.make_str_idx` (:func:`keyring.Keyring.make_idx_str`).
Both need one or more :class:`CoordStr<tomate.coordinates.coord_str.CoordStr>`.


A rant on slices
++++++++++++++++

Tomate will try to convert list of integers indices into slices as much as
possible, since it is the most effective way to subset an array. However it
brings some issues.
It is impossible to obtain the length of what the slice would select before
actually selecting it.
Sometimes, Tomate needs that length, in last resort it will guess it using very
smart math™, see :func:`key.guess_slice_size`. This should happen only scarcely,
and will be logged in debug.

Some functions also need to convert slices into lists of integers, and we need
for that the size of the iterable that is going to be sliced.
Here, no guessing, Tomate will throw an exception if it does not have that
size at hand.

The Keys object can store the size of the parent and of the selection, Tomate
will try its best to do that when needed.

.. currentmodule :: tomate


Accessors
---------

Arrays can be accessed and manipulated using an
:class:`Accessor<accessor.AccessorABC>` object.
This class is a collection of static and class methods, it does not need
instanciation per se.
One can subclass it to modify the implementation of data storage.
By default an :class:`Accessor<accessor.Accessor>` for numpy arrays is used.

It is available as a class attribute of the Variable class
(:attr:`Variable.acs<variable_base.Variable.acs>`),
and of the filegroup class.


Normal and advanced indexing
++++++++++++++++++++++++++++

Tomate allows for indexing the array in ways that are slightly out of the
normal use of numpy indexing.
Namely, asking for lists of indices for multiple dimensions is not
straightforward in numpy. For instance we could think that::

  data[[0, 1], [10, 11, 12], :]

would take the first two indices of the time coordinate, and the indices [10,
11, 12] for the latitude.
However this won't work (see `numpy doc page on indexing
<https://numpy.org/doc/stable/user/basics.indexing.html>`__ for more details).

The accessor will use two methods.
First one is if there is no particular issue with normal indexing.
The keys values are just converted into a tuple and passed to the array (see
:func:`take_normal<accessor.Accessor.take_normal>` and
:func:`place_normal<accessor.Accessor.place_normal>`).

Second way is if there is an issue with normal indexing such that more
complicated means are necessary.
This is the case if there is any combination of integer keys and list keys, or
more than one list key.
In this case, multiple successive access to the array are made,
so `array[0, [0, 1, 2], :, [1]]` is transformed into
`array[0][[0, 1, 2]][:, :][:, :, [1]]`.
To write data, a loop is done.
(see :func:`take_complex<accessor.Accessor.take_complex>`
and :func:`place_complex<accessor.Accessor.place_complex>`)

Examples::

  # Normal indexing
  time=0, lat=2, lon=5
  time=0, lat=slice(None, None), lon=5
  time=[0, 1], lat=slice(None, None), lon=slice(None, None)

  # Complex indexing
  time=0, lat=[1], lon=5
  time=[0, 1], lat=[0, 1, 3, 5], lon=slice(None, None)
  time=[0], lat=[15], lon=[1, 2, 3]

Keys are converted to slices whenever possible, as the accessing is more
straightforward, less error prone, and return a view of the array.


Integers vs lists
+++++++++++++++++

As with numpy normal indexing, an integer key will result in the dimension being
squeezed, but a list of length one (or the corresponding slice) will keep the
dimension.
The expection to this rule is when using
:func:`load<db_types.data_disk.DataDisk.load>` and
:func:`slice_data<data_base.DataBase.slice_data>` (or other functions acting on
the data). The data object will always keep the same number of dimensions.
