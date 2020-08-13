
.. toctree::
   :hidden:

.. currentmodule:: tomate.variables


Variable object
===============

Data is stored in separated arrays for each variable.
The :class:`Variable<variable_base.Variable>` manage the data for one variable.

Variables can have different dimensions (or dimensions in a different order),
and different datatypes.
The range of the data is still managed centrally for all variables by the
database object (with the different scopes). So variables with the same
dimensions will have the same shape.

Each variable can have a specific datatype. For numpy arrays, this would
correspond to the `dtype
<https://numpy.org/devdocs/reference/arrays.dtypes.html>`__.

The user can specify a subclass to use for each variable.
The base class Variable uses a numpy array, but for instance,
:class:`VariablesMasked<masked.variable_masked.VariableMasked>`
uses a masked numpy array to treat missing values.

All those characteristics can be indicated when creating a new variable.
They can be supplied as arguments to
:func:`DataBase.add_variable<tomate.data_base.DataBase.add_variable>`.
If one these argument is missing, Tomate tries to find it in the
:doc:`VI<variables_info>`. First by trying to find the variable specific
attributes '_datatype', '_var_class', '_dims'. Then the same attributes
without the leading underscore, and finally will resort to a default value.
Default for datatype is None, for variable class is
:class:`Variable<variable_base.Variable>`.
Tomate will try to guess the dimensions from filegroup if possileb, if not it
will use all the dimensions available.

Note that these informations can be found automatically during scanning, either
by explicitely using a function scanning variable attributes, such as
:func:`nc.scan_variables_datatype
<tomate.scan_library.nc.scan_variables_datatype>`. Or even with any scanning
function (the VI is always accessible from within scanning functions): for
instance :func:`nc.scan_variables
<tomate.scan_library.nc.scan_variables>` will try to obtain a variable class.

One can also use `DataBase.create_variables` to create all variable objects from
variables in the available scope in one go.


Accessing variables data
------------------------

Data is storred in the 'data' attribute for each variable. But it can
be accessed conveniently using :func:`Variable.view<base.Variable.view>`
or :func:`Variable.view_by_value<base.Variable.view_by_value>`.
To access multiple variables at once one should use
:func:`DataBase.view*<tomate.data_base.DataBase.view>`. In this case it will
return a tuple with multiple arrays. Variables can be reunited in the same array
under certain conditions with the same function using the 'stack' argument.
