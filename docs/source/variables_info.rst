
.. currentmodule :: tomate.variables_info

:ref:

Variables Info
--------------

The database object contains a :class:`VariablesInfo`, abreviated as `VI`.
A vi holds general information about the data, but also attributes specific to a
variable.
For example, we can set and recover a `version` information::

  vi.set_infos(version='2.0')
  print(vi.version)
  print(vi.get_info('version'))

or a variable specific information, for instance a `fullname` attribute::

  vi.set_attributes('U', fullname='East. vel.')
  vi.fullname['U'] = 'East. vel.'
  vi['U'].fullname = 'East. vel.'

As you can see, one can access the information in multiple ways.
The more straightforward is using dedicated functions such as
:func:`VariablesInfo.set_attribute`, :func:`VariablesInfo.set_attributes`,
:func:`VariablesInfo.set_info`, :func:`VariablesInfo.set_infos`,
:func:`VariablesInfo.get_attribute`, :func:`VariablesInfo.get_attribute_default`,
and :func:`VariablesInfo.get_info`.

The second is by attribute or info, by using class attributes, for instance::

  print(vi.fullname)
  print(vi.version)

This returns either the info value or for an attribute an :class:`Attribute`
class, which is a dictionnary with the addition that setting a value will
also affect the VI, by changing or adding a variable attribute::

  attr = vi.fullname
  attr['U'] = 'new'

The last way is by accessing variables as items. This will return a
:class:`VariableAttributes`, which is a dictionnary with the addition that
attributes can be accessed as class attribute, and setting a value will also
affect the VI::

  vattr = vi['U']
  vattr.fullname = 'new'

More operations are available, see :class:`VariablesInfo`.
