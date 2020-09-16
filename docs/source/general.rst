
Introduction to Tomate
======================

Tomate provides ways to manipulate data under the form of multi-dimensional
arrays.
It manages multiples variables, as well as the coordinates along which the data
varies.
It also provides multiple convenience functions to retrieve subpart of the data,
do computations, or plot the data.

The data can be retrieved from disk, where it can be arranged in multiple ways
and formats.
The data can span multiple files and directories.
Information on the data, such as variable attributes, or coordinates values can
be retrieved automatically during the 'scanning' process.

The data, and all information about it, is represented by a python class
instance, the :doc:`DataBase object<data>`.
This object provides:

* :doc:`Coordinates<coord>` which give information on the data coordinates.
  Coordinates objects are grouped in :ref:`Scopes`.
* :doc:`Variables<variable>` which store data for one variable
* :doc:`VariablesInfo<variables_info>` which supply informations about the
  variables, and the data in general.
* Various optional convenience functions
* Eventually, :doc:`Filegroups<filegroup>` which inform on where to find the
  data files, and how to load data from those files.

To help construct these complex objects, a Constructor can be used. It acts as
configuration tool.

To jump right into using the package, one can immediatly go read the
:doc:`constructing a database<tutorial>` doc page.
One can also use :func:`tomate.scan_library.nc.scan_file` to scan
everything in a NetCDF file, without needing to specify anything.
More examples can be found in `/examples
<https://github.com/Descanonge/tomate/blob/master/examples>`__ and a
`showcase
<https://github.com/Descanonge/tomate/blob/master/examples/get_started.ipynb>`__
jupyter notebook.

The package contains many configurable parts, that are as independant of each
other as possible. What can be tweaked or expanded, and how to do it is
explained (in part) in :ref:`Expanding Tomate`.

Important details on how the data is accessed in arrays are available in
:ref:`Accessing data`.

Information on the files scanning process is put in :ref:`Scanning`.

And of course, the :doc:`API reference<_references/tomate>` contains all the doc
strings for all modules, classes, and functions.


Source code: `<https://github.com/Descanonge/tomate>`__
