
.. currentmodule :: data_loader

:ref:

Variables Info
==============

All data objects contains a
:class:`VariablesInfo<variables_info.VariablesInfo>`, abreviated
as `vi`.
A vi holds general information about the data, but also attributes specific to a
variable. Each attribute is an
:class:`IterDict<iter_dict.IterDict>`, an ordered dictionnary that
can be accessed from variable name or index.
For example, we can set and recover a 'velocities' attribute::

  vi.add_infos('velocities', ['U', 'V'])
  print(vi.velocites)
  print(vi.get_info('velocities'))

or a variable specific information, for instance `fullname` attribute for
different variables::

  vi.fullname[['U', 'V']]
  vi.get_attr('fullname', 'U')


Only some variables of the vi can be selected::

  new_vi = vi[['U', 'S']]
  new_vi = vi[0:2]


More operations are available, see :class:`variables_info.VariablesInfo`.
