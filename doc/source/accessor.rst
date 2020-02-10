
.. currentmodule :: data_loader

Accessing data
====================

The package provides some low-level functions to access the data (loaded or
on disk), in a controlled fashion. This create an abstraction level, and
allows to change the implementation of how the data is stored.
The data is still directely accessible.

This page describes the api for accessing data this way.

Keyrings
--------

In multiple places of the package, data has to be selected according
to indices of the data coordinates.
A selection along a coordinate is done using a 'key'. It can be an integer,
a list of integer, or a slice.
Multiple keys are regrouped into a single object: a
:class:`Keyring<key.Keyring>`.
This object is similar to a dictionnary. The keys are stored in a
:class:`Key<key.Key>` class.
In the rest of the documentation a key designates either a Key object, or the
actual variable the user is demanding.
A 'key-like object', or a 'key value' designates unambiguously the latter.

A keyring provides many useful functions to manipulate the indices a user
is demanding, as well as different attributes and methods to iterate through
the coordinates, keys, key-like values it contains.
A lot of function in the package still take a serie of key-like keyword
arguments, the easiest way to convert a keyring to keywords arguments is::

  some_function(**keyring.kw)

Some functions can take both a keyring and keys in argument. The class function
:func:`key.Keyring.get_default` combines the two argument. It also make a copy
of the keyring, to avoid in-place modifications.
Developpers are invited to look at the API doc-strings for further information.


Accessors
---------

Arrays can be accessed and manipulated using a
:class:`Accessor<accessor.Accessor>` object.
This class is a collection of static and class methods,
it does not need instanciation per se.
One can subclass it to modify the implementation of data storage.

It is available a class attribute of the Data class
(:attr:`Data.acs<data_base.DataBase.acs>`),
and of the filegroup class.
It can be changed either by writing a subclass of Data, or when dynamically
creating a data class using the constructor.

The base accessor is written for standard numpy arrays.


Normal and advanced indexing
----------------------------

The package allows for indexing the array in ways that are slightly out
of the normal use of numpy indexing.
Namely, asking for lists of indices for different dimensions is
not straightforward in python. For instance we could think that::

  data[[0, 1], [10, 11, 12], :]

would take the first two indices of the time coordinate,
and the indices [10, 11, 12] for the latitude.
However this won't work (see numpy doc page on indexing for more details).

The accessor object can take care of the distinction between
normal and advanced indexing, and choose between two ways
of accessing an array when taking values from the array,
or assigning them a value (ie placing values),
depending on the demanded keyring.

First way is if there is no particular issue with normal indexing.
The keys values are then converted into a tuple and passed to the array
(see :func:`get_array_simple<accessor.Accessor.take_normal>`
and :func:`place_simple<accessor.Accessor.place_normal>`).

Second way is if there is an issue with normal indexing such that more complicated
means are necessary.
This is the case if there is any combination of integer keys and list keys,
or more than one list key.
In this case, multiple successive access to the array are made,
so `array[0, [0, 1, 2], :, [1]]` is transformed into
`array[0][[0, 1, 2]][:, :][:, :, [1]]`.
To write data, a loop is done.
(see :func:`get_array_complex<accessor.Accessor.take_complex>`
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

It is important to note that in the complex case, the returned array will be a copy
and not a view of the original index.
Keys are converted to slices whenever possible, as the accessing is more
straightforward, less error prone, and return a view of the array.


Integers vs lists
-----------------

As with numpy normal indexing, an integer key will result in the dimension
being squeezed, but a list of length one (or the corresponding slice) will
keep the dimension.
The expection to this rule is when using
:func:`load_data<data_base.DataBase.load_data>` and
:func:`slice_data<data_base.DataBase.slice_data>` (or other functions
acting on the data attribute). The data object will always keep the same number
of dimensions.
