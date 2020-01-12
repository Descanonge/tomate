"""Add convenience functions for various operations on data."""

import numpy as np

from data_loader.data_base import DataBase


class DataCompute(DataBase):
    """Added functionalities for various computations."""

    def gradient(self, variable, coords):
        """Compute a n-dimensional gradient.

        Parameters
        ----------
        variable: str
        coords: List[str]
            Coordinates to compute the gradient along.
        """
        self._check_loaded()
        axis = [self.coords_name.index(c) for c in coords]
        values = [self.coords[c][:] for c in coords]

        if 'DataMasked' in self.bases:
            self.filled(fill, variables=variable)
        else:
            data = self[variable]
        grad = np.gradient(data, *values, axis=axis)
        return grad

    def gradient_magn(self, variable, coords=None):
        """Compute the gradient magnitude.

        See also
        --------
        gradient: Compute the gradient.
        """
        grad = self.gradient(variable, coords)
        magn = np.linalg.norm(grad, axis=0)

        if np.ma.isMaskedArray(self.data):
            mask = self[variable].mask.copy()
            magn = np.ma.array(magn, mask=mask)
        return magn

    def derivative(self, variable, coord):
        """Compute derivative along a coordinate.

        Other coordinates are looped over.

        Parameters
        ----------
        variable: str
        coord: str
        """
        der = self.gradient_nd(variable, [coord])
        return der

    def apply_on_subpart(self, func, variables=None, args=None, kwargs=None, **kw_coords):
        """Apply function on data subset.

        Parameters
        ----------
        """
        self._check_loaded()
        if variables is None:
            variables = self.vi.var
        if isinstance(variables, str):
            variables = [variables]

        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}

        idx = self.vi.idx[variables]
        kw_coords = self.get_coords_full(**kw_coords)
        kw_coords = self.get_none_total(**kw_coords)
        key = tuple([idx, *kw_coords.values()])

        data = self.data[key]
        res = func(data, *args, **kwargs)
        return res

    def mean(self, variables=None, coords=None, kwargs=None, **kw_coords):
        """Compute average on a given window.

        Parameters
        ----------
        variables: str or List[str]
        coords: List[str]
            Coordinates to compute the mean along.
        kwargs: Dict
            Argument passed to numpy.nanmean
        kw_coords: Dict, optional
            Part of the data to consider for averaging (by index).
        """
        if coords is None:
            coords = self.coords_name
        axes = tuple([self.coords_name.index(c)+1 for c in coords])

        if kwargs is None:
            kwargs = {}

        mean = self.apply_on_subpart(np.nanmean, variables,
                                     args=[axes], kwargs=kwargs, **kw_coords)
        return mean

    def std_dev(self, variables=None, coords=None, kwargs=None, **kw_coords):
        """Compute standard deviation on a given window."""
        if coords is None:
            coords = self.coords_name
        axes = tuple([self.coords_name.index(c)+1 for c in coords])

        if kwargs is None:
            kwargs = {}

        mean = self.apply_on_subpart(np.nanstd, variables,
                                     args=[axes], kwargs=kwargs, **kw_coords)
        return mean

    def linear_combination(self):
        """Compute linear combination between variables."""
        raise NotImplementedError


def do_stack(func, ndim, array, *args, axes=None, output=None, **kwargs):
    """Apply func over certain axes of array. Loop over remaining axes.

    Parameters
    ----------
    func: Callable
        Function which takes a slice of array.
        Dimension of slice is dictated by `ndim`.
    ndim: int
        The number of dimensions func works on. The remaining dimension
        in input array will be treated as stacked and looped over.
    array: Array
    axes: List[int]
        Axes that func should work over, default is the last ndim axes.
    output:
        Result passed to output. default to np.zeros.
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
