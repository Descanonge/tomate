
.. currentmodule :: data_loader


Database
========

The data object is the main focus of this package,
and main gateway to its functionalities.
It holds the data array itself when loaded, and all the information
about variables, coordinates, and files on disk.
It contains a variety of function to load, select, slice,
do computations on, or to plot the data.

* To learn how data files are managed, see :doc:`filegroup`.
* To learn how information on data and variales are stored see
  :doc:`variables_info`.


Scopes
------

The data is stored in a multidimensional array.
The first axis of the array corresponds to the different variables,
and the following axes to the coordinates, in the order they are
passed to the data object at its creation.

Information about the data dimensions is contained in
:class:`scopes<scope.Scope>`.
This object holds a list of variables, and of
:doc:`coordinates objects<coord>`.

The data object contains 3 different scopes by default.

+---------+----------------+------------------------+
|Name     |Variable name   |Description             |
+---------+----------------+------------------------+
|available|`avail`         |Data that is available  |
|         |                |on disk                 |
+---------+----------------+------------------------+
|loaded   |`loaded`        |Data that is currently  |
|         |                |loaded in memory        |
+---------+----------------+------------------------+
|select   |`select`        |Data that is selected   |
+---------+----------------+------------------------+

Some attributs in scopes can be accessed directly from
the data object as attributes for convenience.
The scope they are taken from is the loaded one, if data
has been loaded, or available otherwise.
In a similar fashion, the `scope` attribute return either the
loaded or available scope object.

All data coordinates can be accessed as attributes, for
instance: `data.lat` is equivalent to `data.scope.lat`,
itself equivalent to `data.avail.lat` if data has not
been loaded yet.

Similarly, the index of each variable in the data array
is found in the `idx` attribute.

Various functions act on the current scope (either
loaded or available). The method docstring should contain
information on the scope they are acting on.
For instance,
:func:`data_base.DataBase.load_data`
acts on available scope, such that::

  dt.load_data(None, lat=slice(10, 30))

will load a part of the data on disk, corresponding to the index
10 to 30 of all the **available** latitude coordinate.

Extra care should be taken to make sure one is working on
the relevant scope.


Additional methods
------------------

The base type for the data object
(:class:`data_base.DataBase`)
provides all functions for data manipulation (loading,
slicing, viewing).
Adding more features can easily be done by creating a subclass, and adding
or overwritting methods.
But one may want to use different features for different datasets, and
combine those features in an organic way.

To this end, the package can dynamically create a new data class, combining
different subclasses of DataBase.
See
:func:`constructor.create_data_class` and
:func:`constructor.Constructor.make_data`.
Note that the classes should be specified in order of priority for method
resolution.
If a clashing in the methods names should arise, warnings will be ensued.
