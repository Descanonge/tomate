


data\_loader.custom\_types
==========================

.. py:module:: data_loader.custom_types

Defines custom types.

NB: Sphinx current support of TypeVar is not extensive, so to have
internal hyperlinks they are here marked as 'classes'. They are actually
TypeVar.


.. rubric:: Contents

.. py:class:: KeyLike

   | Key for indexing data by index or variable name.
   | `KeyLikeInt, KeyLikeVar`

.. py:class:: KeyLikeInt

   | Key for indexing array or generic coordinate.
   | `int, List[int], slice, None`

.. py:class:: KeyLikeStr

   | Key for indexing named coordinates using strings.
   | `str, List[str], slice, None`

.. py:class:: KeyLikeVar

   | Key for indexing Variables. Support integers and strings.
   | `KeyLikeStr, KeyLikeVar`

.. py:class:: KeyLikeFloat

   | Key support for floats.
   | `int, float, List[Union[int, float]], slice, None`

.. py:class:: KeyLikeValue

   | Key for indexing coordinate by value, using floats or strings.
   | `KeyLikeInt, KeyLikeVar`

.. py:class:: File

   Object for manipulating an open file.



..
