
:ref:

Variables Info
==============

All data objects contains a
:class:`VariablesInfo<data_loader.variables_info.VariablesInfo>`, abreviated
as `vi`.
A vi holds general information about the data, but also attributes specific to a
variable. Each attribute is an
:class:`IterDict<data_loader.iter_dict.IterDict>`, an ordered dictionnary that
can be accessed from variable name or index.
For example, we can recover the `fullname` attribute for different variables::

  vi.fullname[['U', 'V']]

The vi also know the position of each variable in the data array. This position
can be obtained as::

  index = vi.idx['variable name']

