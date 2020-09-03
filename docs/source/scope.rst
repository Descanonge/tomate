
.. currentmodule:: tomate

Scopes
------

Multiple :doc:`coordinates objects<coord>` are stored together
in a :class:`Scope<scope.Scope>`.
By default, the database object contains 3 different scopes,
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

Some methods act on a specific scope. The scope by default (or `current`) is
`loaded` if data has been loaded, `available` otherwise.
The method docstring should contain information on the scope
they are acting on.
For instance,
:func:`load<db_types.data_disk.DataDisk.load>`
acts on available scope, such that::

  db.load(lat=slice(10, 30))

will load a part of the data on disk, corresponding to the index
10 to 30 of all the **available** latitude coordinate.
Extra care should be taken to make sure one is working on
the relevant scope.

All data dimensions can be accessed as attributes, for
instance: `data.lat` is equivalent to `data.scope.lat`,
itself equivalent to `data.avail.lat` if data has not
been loaded yet.

Scopes can be derived from other scopes, for instance by using
:func:`DataBase.get_subscope<data_base.DataBase.get_subscope>` or
:func:`DataBase.get_subscope_by_value<data_base.DataBase.get_subscope_by_value>`.
Such scope has :attr:`parent_scope<scope.Scope.parent_scope>` and
:attr:`parent_keyring<scope.Scope.parent_keyring>` attributes.
They can be defined as::

  scope = scope.parent_scope.slice(scope.parent_keyring)
