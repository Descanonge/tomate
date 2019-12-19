
Expanding the package
=====================

Some classes can be extended, some are meant to be subclassed.
Here are some information on where to start to expand the package.

File formats
------------

To use a new file format, one should subclass
:class:`FilegroupLoad<data_loader.filegroup.FilegroupLoad>`, and
overwrite a couple of functions.

First
:func:`open_file<data_loader.filegroup.filegroup_scan.FilegroupScan.open_file>`
and
:func:`close_file<data_loader.filegroup.filegroup_scan.FilegroupScan.close_file>`
should be implemented.
`open_file` should return a file object passed to various scanning and loading
functions. Exception handling is already taken care of by the package.

Then the
:func:`load_cmd<data_loader.filegroup.FilegroupLoad.load_cmd>` function should
be implemented. For more details, see :ref:`Executing the command`.

All those functions should handle logging, especially the loading function, in
which the log provides means to check if the correct data is loaded. See
:doc:`log`.
It is advised to look at
:class:`FilegroupNetCDF<data_loader.filegroup.FilegroupNetCDF>`
for a practical example of a file format.

A new file format will recquire new scanning function. One can take example
at the :mod:`scan_library<data_loader.scan_library>` module.


Data base type
--------------

Additional features can be added to the data base object.
One can look at
:class:`DataMasked<data_loader.masked.DataMasked>` for inspiration.

See :ref:`Data Base`


Coordinates subclasses
----------------------

See :doc:`coord`
