
.. toctree::
   :hidden:

.. currentmodule:: tomate.variables


Variable object
===============

Data is actually stored in separated arrays for each variable.
The :class:`Variable<base.Variable>` manage the data for one variable.

The range of the data is still managed centrally for all variables
by the database object (with the different scopes).
So variables with the same dimensions will have the same shape.

Variable specific
-----------------

The user can specify a subclass to use for each variable.
The base class Variable uses a numpy array, but for instance,
:class:`VariablesMasked<masked.variable_masked.VariableMasked>`
uses a masked numpy array to treat missing values.

Each variable can vary along different dimensions (or in different order).
Each variable can also have a specific datatype. For numpy arrays, this
would correspond to the `dtype <https://numpy.org/devdocs/reference/arrays.dtypes.html>`__.

Theses characteristics can be indicated when creating a new variable with
:func:`DataBase.add_variable<tomate.data_base.DataBase.add_variable>`.
It can also be found automatically during scanning. Dimensions is a mandatory
element to scan or set, and datatype dataclass can be scanned as a variable
specific attribute and put in the VI. Any variable attribute named 'datatype'
or 'var_class' will be used unless overriden manualy.

Accessing variables data
------------------------

Data is storred in the 'data' attribute for each variable. But it can
be accessed conveniently using :func:`Variable.view<base.Variable.view>`
or :func:`Variable.view_by_value<base.Variable.view_by_value>`.
To access multiple variables at once one should use
:func:`DataBase.view*<tomate.data_base.DataBase.view>`. In this case it
will return a tuple with multiple arrays. Variables can be reunited in
the same array under certain condition with the same function using
the 'stack' argument.
