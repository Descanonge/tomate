
.. currentmodule:: tomate


The Database object
===================

The data object is the main focus of this package,
and main gateway to its functionalities.
It holds the data array itself when loaded, and all the informations
about variables, coordinates, and files on disk.
It contains a variety of functions to load, select, slice,
do computations on, or plot the data.

* To learn how coordinates are managed, see :ref:`Coordinates` and
  :ref:`Scopes`.
* To learn how data files are managed, see :ref:`Filegroups`.
* To learn how information on data and variables are stored see
  :ref:`Variables Info`.


.. toctree::
   :hidden:

   coord
   scope
   variable
   filegroup
   variables_info


Database features
-----------------

Selection
^^^^^^^^^

A useful feature is the selection scope. It allows to create
a new scope and manipulate it before sending it to some methods.

The scope is created from the available scope (by default) with the
:func:`select<data_base.DataBase.select>` and
:func:`select_by_value<data_base.DataBase.select_by_value>` methods.
One can also use :func:`add_to_selection<data_base.DataBase.add_to_selection>`
to expand the selection, or
:func:`Scope.slice<scope.Scope.slice>` to reduce the selection.

We can then use functions such as
:func:`load_selected<db_types.data_disk.DataDisk.load_selected>`
or :func:`view_selected<data_base.DataBase.view_selected>`.
Both these methods can further slice the selection before doing their job
(without modifying the selected scope)::

  dt.select(time=slice(0, 50), var='SST')
  dt.load_selected(time=0)


Additional methods
^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^^^^^^^

It can be useful to apply some operations each time data is loaded.
One can add multiple functions that will be called each time specific variables
are loaded. These function can also tied to a specific filegroup.
This is done by using
:func:`Constructor.add_post_loading_func<constructor.Constructor.add_post_loading_func>`.
