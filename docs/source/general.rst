
Introduction to Tomate
======================

Tomate provides ways to manipulate data under the form of a
multi-dimensional array.
It manages multiples variables, as well as the coordinates along
which the data varies.
It also provides multiple convenience functions to retrieve
subpart of the data, do computations, or plot the data.

The data can be retrieved from disk, where it can be arranged
in multiple ways and formats.
The data can span multiple files and directories.
Information on the data, such as variable attributes,
or coordinates values can be retrieved automatically
during the 'scanning' process.

The data, and all information about it, is represented by a
python class instance, see :doc:`data`.
This object provides:

* :doc:`Coordinates<coord>` which give information on the data
  coordinates, (or dimensions). Coordinates objects are grouped
  in :ref:`Scopes`.
* :doc:`VariablesInfo<variables_info>` which supply
  information about the variables, and the data in general.
* Various optional convenience functions
* Eventually, :doc:`Filegroups<filegroup>` which inform on where to
  find the data files, and how to load data.

To help construct these complex objects, a Constructor can be used. It acts as
configuration tool. Examples can be found in /examples.

To jump right into using the package, one can immediatly go read the
:doc:`constructing a database<tutorial>` doc page.

The package contains many configurable parts, that are as independant of each
other as possible. What can be tweaked or expanded, and how to do it is
explained (in part) in :ref:`Expanding the package`.

Important details on how the data is accessed in arrays are available
in :ref:`Accessing data`.

Information on the files scanning process is put in
:ref:`Scanning`.

And of course, the :doc:`API reference<_references/tomate>` contains all
the doc strings for all modules, classes, and functions.


Github page: `<https://github.com/Descanonge/tomate>`__