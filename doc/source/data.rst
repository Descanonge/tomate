
.. currentmodule :: data_loader


Database
========

The data object is the main focus of this package,
and main gateway to its functionalities.
It holds the data array itself when loaded, and all the informations
about variables, coordinates, and files on disk.
It contains a variety of functions to load, select, slice,
do computations on, or plot the data.

* To learn how data files are managed, see :doc:`filegroup`.
* To learn how information on data and variables are stored see
  :doc:`variables_info`.


Scopes
------

The data is stored in a multidimensional array.
The first axis of the array corresponds to the different variables,
and the following axes to the coordinates, in the order they are
passed to the data object at its creation.
Note: this is the default behavior, but if a Variables
object is specified when creating a Constructor, variables does not have
to be on the first dimension (this is experimental though).


Information about the dimensions is contained in
:class:`scopes<scope.Scope>`.
This object holds a list of variables, and of the
:doc:`coordinates objects<coord>`.

By default, the data object contains 3 different scopes,
each corresponding to a specific range of data.

+-----------+----------------+------------------------+
|Name       |Variable name   |Description             |
+-----------+----------------+------------------------+
|available  |`avail`         |Data that is available  |
|           |                |on disk                 |
+-----------+----------------+------------------------+
|loaded     |`loaded`        |Data that is currently  |
|           |                |loaded in memory        |
+-----------+----------------+------------------------+
|selected   |`selected`      |Data that is selected   |
+-----------+----------------+------------------------+

Some methods act on a specific scope. The scope by default is
'loaded' if data has been loaded, 'available' otherwise.
The method docstring should contain
information on the scope they are acting on.
For instance,
:func:`data_base.DataBase.load`
acts on available scope, such that::

  dt.load(None, lat=slice(10, 30))

will load a part of the data on disk, corresponding to the index
10 to 30 of all the **available** latitude coordinate.
Extra care should be taken to make sure one is working on
the relevant scope.

Some scope attributes can be accessed directly from
the data object for convenience.
The scope they are taken from is the loaded one, if data
has been loaded, or available otherwise.
In a similar fashion, the `scope` attribute return either the
loaded or available scope object.

All data coordinates can be accessed as attributes, for
instance: `data.lat` is equivalent to `data.scope.lat`,
itself equivalent to `data.avail.lat` if data has not
been loaded yet.

Scopes can be derived from other scopes, for instance by using
:func:`DataBase.get_subscope<data_base.DataBase.get_subscope>` or
:func:`DataBase.get_subscope_by_value<data_base.DataBase.get_subscope_by_value>`.
Such scope has :attr:`parent_scope<scope.Scope.parent_scope>` and
:attr:`parent_keyring<scope.Scope.parent_keyring>` attributes.
The can be defined as::

  scope = scope.parent_scope.slice(scope.parent_keyring)

* More information on :doc:`coordinates<coord>`
* More information on :ref:`Variables`


Selection
---------

A useful feature is the selection scope. It allows to create
a new scope and manipulate it before sending it to some methods.

The scope is created from the available scope (by default) with the
:func:`select<data_base.DataBase.select>` and
:func:`select_by_value<data_base.DataBase.select_by_value>` methods.
One can also use :func:`add_to_selection<data_base.DataBase.add_to_selection>`
to expand the selection, or
:func:`Scope.slice<scope.Scope.slice>` to reduce the selection.

We can then use functions such as
:func:`load_selected<data_base.DataBase.load_selected>`
or :func:`view_selected<data_base.DataBase.view_selected>`.
Both these methods can further slice the selection before doing their job
(without modifying the selected scope)::

  dt.select(time=slice(0, 50), var='SST')
  dt.load_selected(time=0)


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
:func:`constructor.Constructor.set_data_types`.
Note that the classes should be specified in order of priority for method
resolution.
If a clashing in the methods names should arise, warnings will be ensued.

For instance, `set_data_types([DataMasked, DataPlot])` will set a database
supporting masked values, and plotting functions.


Post loading function
---------------------

It can be useful to apply some operations each time data is loaded.
One can add multiple functions that will be called each time specific variables
are loaded. These function can also tied to a specific filegroup.
This is done by using
:func:`Constructor.add_post_loading_func<constructor.Constructor.add_post_loading_func>`.
