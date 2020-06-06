
.. currentmodule:: data_loader

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
:func:`load<db_types.data_disk.DataDisk.load>`
acts on available scope, such that::

  db.load(None, lat=slice(10, 30))

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

* More information on :ref:`Coordinates`
* More information on :ref:`Variables`
