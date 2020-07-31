"""Apply function over certain axes of array."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import Any, Callable, List

import numpy as np

from tomate.custom_types import Array


def do_stack(func: Callable, ndim: int,
             array: Array, *args: Any,
             axes: List[int] = None,
             output=None, **kwargs: Any):
    """Apply func over certain axes of array. Loop over remaining axes.

    :param func: Function which takes a slice of array.
        Dimension of slice is dictated by `ndim`.
    :param ndim: The number of dimensions func works on. The remaining dimension
        in input array will be treated as stacked and looped over.
    :param axes: Axes that func should work over, default is the last ndim axes.
    :param output: Result passed to output. default to np.zeros.
    """
    if axes is None:
        axes = list(range(-ndim, 0))
    lastaxes = list(range(-ndim, 0))

    # Swap axes to the end
    for i in range(ndim):
        array = np.swapaxes(array, axes[i], lastaxes[i])

    # Save shape
    stackshape = array.shape[:-ndim]

    if output is None:
        output = np.zeros(array.shape)

    # Place all stack into one dimension
    array = np.reshape(array, (-1, *array.shape[-ndim:]))
    output = np.reshape(output, (-1, *output.shape[-ndim:]))

    for i in range(array.shape[0]):
        output[i] = func(array[i], *args, **kwargs)

    array = np.reshape(array, (*stackshape, *array.shape[-ndim:]))
    output = np.reshape(output, (*stackshape, *output.shape[-ndim:]))

    # Reswap axes
    for i in range(ndim):
        array = np.swapaxes(array, axes[i], lastaxes[i])
        output = np.swapaxes(output, axes[i], lastaxes[i])

    return output
