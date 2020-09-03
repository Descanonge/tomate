


tomate.custom\_types
====================

.. py:module:: tomate.custom_types

Defines custom types.

NB: Sphinx current support of TypeVar is not extensive, so to have
internal hyperlinks they are here marked as 'classes'. They are actually
TypeVar.


.. rubric:: Contents

.. py:class:: Array

   Multi-dimensional array similar to a numpy array.


.. py:class:: File

   Object for manipulating an open file.


.. py:class:: KeyLike

   | Key for subsetting data by index or name for string coordinates.
   | `KeyLikeInt, KeyLikeVar`

.. py:class:: KeyLikeInt

   | Key for subsetting arrays or generic coordinates by index.
   | `int, List[int], slice, None`

.. py:class:: KeyLikeStr

   | Key for subsetting string coordinates using strings.
   | `str, List[str], slice, None`

.. py:class:: KeyLikeFloat

   | Key for subsetting coordinates by float value.
   | `int, float, List[Union[int, float]], slice, None`

.. py:class:: KeyLikeValue

   | Key for subsetting coordinate by value, using floats or strings.
   | `KeyLikeInt, KeyLikeVar`

