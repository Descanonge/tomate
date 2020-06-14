"""Defines custom types. """

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import List, Union, TypeVar

Array = TypeVar('Array')

KeyLikeInt = TypeVar('KeyLikeInt', int, List[int], slice, None)

KeyLikeStr = TypeVar('KeyLikeStr', str, List[str], slice, None)
KeyLikeVar = TypeVar('KeyLikeVar', KeyLikeInt, KeyLikeStr)

KeyLikeFloat = TypeVar('KeyLikeFloat', int, float, List[Union[int, float]], slice, None)
KeyLikeValue = TypeVar('KeyLikeValue', KeyLikeFloat, KeyLikeStr)

KeyLike = TypeVar('KeyLike', KeyLikeInt, KeyLikeVar)

File = TypeVar('File')
