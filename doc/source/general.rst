
Introduction to Data Loader
===========================

Data Loader allows to load data that can span different files and directories,
and that can be accessed in various ways. The data must be all on the same grid.

The data, and all information about it, is represented by a python class
instance, derived from :doc:`DataBase<data_base>`.
The data object needs also:

* :doc:`Coordinates<coord>` which give information on the data
  coordinates, or dimensions
* :doc:`VariablesInfo<variables_info>` which supply
  information about the variables available
* :doc:`Filegroups<filegroup>` which inform on where to
  find the data files, and how to load data.

To help construct these complex objects, a Constructor is used. It acts as
configuration tools. Examples can be found in /examples.

To jump right into using the package, one can immediatly go read the
:doc:`constructing a database<tutorial>` doc page.
