
.. currentmodule :: tomate


Expanding Tomate
================

Some classes can be extended, some are meant to be subclassed.
Here are some information on where to start to expand the package.

File formats
------------

To use a new file format, one should subclass
:class:`FilegroupLoad<filegroup.filegroup_load.FilegroupLoad>`, and
overwrite a couple of functions.

First :func:`open_file<filegroup.filegroup_scan.FilegroupScan.open_file>`.
`open_file` should return a file object passed to various scanning and loading
functions. Exception handling is already taken care of by the package.

Then the
:func:`load_cmd<filegroup.filegroup_load.FilegroupLoad.load_cmd>` function
should be implemented.
For more details, see :ref:`Executing the command`.

All those functions should handle logging, especially the loading function, in
which the log provides means to check if the correct data is loaded. See
:doc:`log`.
It is advised to look at
:class:`FilegroupNetCDF<filegroup.filegroup_netcdf.FilegroupNetCDF>`
for a practical example of a file format expansion.

A new file format will recquire new scanning function. One can take example
at the :mod:`tomate.scan_library.nc`.


Data base type
--------------

Additional features can be added to the data base object.
Any method can be added to or modified from the
:class:`DataBase<data_base.DataBase>` class by creating a subclass.
The data object class can then be chosen from any  subclasses, or from a
combination of thoses.
See :ref:`Additional methods` for details.

One can look at
:class:`DataCompute<db_types.data_compute.DataCompute>` and
:class:`DataPlot<db_types.plotting.data_plot.DataPlot>`
for inspiration.

It is also possible to change how the data is stored, or accessed.
To do that, it is necessary to modify the :ref:`Accessors` class.


Coordinates subclasses
----------------------

See :doc:`coord`.


Variables subclasses
--------------------

See :doc:`variable`.
