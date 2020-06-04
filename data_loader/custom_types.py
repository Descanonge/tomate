"""Defines custom types.


:attr KeyLike: TypeVar: Key for indexing array or generic coordinate.
:attr KeyLikeStr: TypeVar: Key for indexing named coordinates using strings.
:attr KeyLikeVar: TypeVar: Key for indexing Variables. Support integers and strings.
:attr KeyLikeFloat: TypeVar: Key support for floats.
:attr KeyLikeValue: TypeVar: Key for indexing coordinate by value, using floats or strings.

:attr File: Type: Object for manipulating an open file.
"""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK

from typing import Any, List, Union, TypeVar

Array = TypeVar('Array')

KeyLikeInt = TypeVar('KeyLikeInt', int, List[int], slice, None)

KeyLikeStr = TypeVar('KeyLikeStr', str, List[str], slice, None)
KeyLikeVar = TypeVar('KeyLikeVar', KeyLikeInt, KeyLikeStr)

KeyLikeFloat = TypeVar('KeyLikeFloat', int, float, List[Union[int, float]], slice, None)
KeyLikeValue = TypeVar('KeyLikeValue', KeyLikeFloat, KeyLikeStr)

KeyLike = TypeVar('KeyLike', KeyLikeInt, KeyLikeVar)

File = Any

