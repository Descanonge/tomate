
.. currentmodule :: data_loader.keys

Accessing data
==============

The package provides some low-level functions to access the data (loaded or
on disk), in a controlled fashion. This create an abstraction level, and
allows to change the implementation of how the data is stored.
The data is still directely accessible.

This page describes the api for accessing data this way.

Selecting parts of arrays
-------------------------

It is often needed to select data in an array by index.
A selection along a dimension is done using a 'key'. It can be an integer,
a list of integer, or a slice.
One should use the right coordinate objects (ie in the right scope) to
find the indices corresponding to wanted values.

Keys and keyrings
+++++++++++++++++

Multiple keys are regrouped into a single object: a
:class:`Keyring<keyring.Keyring>`.
This object is similar to a dictionnary. The keys are stored in a
:class:`Key<key.Key>` class.
In the rest of the documentation a key designates either a Key object, or the
actual indices the user is demanding.
A 'key-like object', or a 'key value' designates unambiguously the latter.

A keyring provides many useful functions to manipulate the indices a user
is demanding, as well as different attributes and methods to iterate through
the coordinates, keys, key-like values it contains.
A lot of functions in the package only take a serie of key-like keyword
arguments, the easiest way to convert a keyring to keywords arguments is::

  some_function(**keyring.kw)

Some functions can take both a keyring and keys in argument. The class function
:func:`keyring.Keyring.get_default` combines the two argument. It also make a copy
of the keyring, to avoid in-place modifications.
Developpers are invited to look at the API doc-strings for further information.

The shape of a key designates the length a coordinate would have after the key
is applied. A shape 0 means it would return a scalar.
None keys have a shape 0 as when taking data from file, a None in-file index
means that dimension is already squeezed.
Shape of slices keys will be infered if possible, but sometimes the shape of the
coordinate on which the slice will be applied is necessary. It is stored in the
:attr:`key.Key.parent_size` attribute once set.

The :attr:`keyring.Keyring.shape` property will return the shape of the array
it would give. Dimensions of size 0 are thus omitted. None indicates the shape
of that dimension is unknown.


Variables Keys
++++++++++++++

The variable dimension can be accessed using both index and variables names.
Both can be useful in different situations.
In most cases though, the user will be inputing variables names, and
it is the methods job to convert it to an index if needed
(whereas the user is expected to find the index for other coordinates).

The subclass :class:`key.KeyVar` supports both as well, it can consists
of an integer, a string, a list of integers or strings, or a slice of
integer or strings.
One can go from variable name to index (or vice-versa) using
:func:`key.KeyVar.make_var_idx` (:func:`key.KeyVar.make_idx_var`).
Both need a Variables object to make the conversion.

The keyring will automatically create a key with this class when it is
named 'var'.
The afore-mentioned methods are also available in the keyring.

Nearly all functions work as well for normal keys as for variable keys,
though slices of strings can miss some functionalites, and are to be avoided.


.. currentmodule :: data_loader

Accessors
---------

Arrays can be accessed and manipulated using an
:class:`Accessor<accessor.Accessor>` object.
This class is a collection of static and class methods,
it does not need instanciation per se.
One can subclass it to modify the implementation of data storage.

It is available as a class attribute of the Data class
(:attr:`Data.acs<data_base.DataBase.acs>`),
and of the filegroup class.
It can be changed either by writing a subclass of Data (or FilegroupLoad),
or when dynamically creating a data class using the constructor.

The default accessor is written for standard numpy arrays.


Normal and advanced indexing
++++++++++++++++++++++++++++

The package allows for indexing the array in ways that are slightly out
of the normal use of numpy indexing.
Namely, asking for lists of indices for multiple dimensions is
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
(see :func:`take_normal<accessor.Accessor.take_normal>`
and :func:`place_normal<accessor.Accessor.place_normal>`).

Second way is if there is an issue with normal indexing such that more complicated
means are necessary.
This is the case if there is any combination of integer keys and list keys,
or more than one list key.
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

It is important to note that in the complex case, the returned array will be a copy
and not a view of the original index.
Keys are converted to slices whenever possible, as the accessing is more
straightforward, less error prone, and return a view of the array.


Integers vs lists
+++++++++++++++++

As with numpy normal indexing, an integer key will result in the dimension
being squeezed, but a list of length one (or the corresponding slice) will
keep the dimension.
The expection to this rule is when using
:func:`load<data_base.DataBase.load>` and
:func:`slice_data<data_base.DataBase.slice_data>` (or other functions
acting on the data attribute). The data object will always keep the same number
of dimensions.
