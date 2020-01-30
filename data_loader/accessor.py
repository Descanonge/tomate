"""Access to data array."""


import logging
from typing import List

import numpy as np


log = logging.getLogger(__name__)


class Accessor():
    """Manages access to arrays.

    Stores static and class methods.
    Can be subclassed for different implementation.

    See :doc:`../accessor`.
    """

    @staticmethod
    def ndim(array) -> int:
        """Return number of dimensions of array."""
        return array.ndim

    @staticmethod
    def shape(array) -> List[int]:
        """Return shape of array."""
        return list(array.shape)

    @classmethod
    def check_dim(cls, keyring, array):
        """Check if keyring match array rank.

        Parameters
        ----------
        keyring: Keyring, Dict, List
            Keys used for creating the array.
        array: Array
        """
        if cls.ndim(array) != len(keyring):
            raise IndexError("Mismatch between selected data "
                             "and keyring length (shape: %s, keyring length: %s)"
                             % (cls.shape(array), len(keyring)))

    @classmethod
    def check_shape(cls, keyring, array):
        """Check if keyring match array shape.

        Parameters
        ----------
        keyring: Keyring
            Keys used for creating the array.
        array: Array
        """
        if any(k is not None and a != k
                for a, k in zip(cls.shape(array), keyring.shape)):
            raise ValueError("Mismatch between selected data "
                             "and keyring shape (array: %s, keyring: %s)"
                             % (cls.shape(array), keyring.shape))

    @classmethod
    def has_normal_access(cls, keyring):
        """Check if keyring would need complex access.

        Parameters
        ----------
        keyring: Keyring
        """
        n_list = [k.type for k in keyring.keys].count('list')
        n_int = [k.type for k in keyring.keys].count('int')
        if n_list >= 2:
            return False
        if n_list > 1 and n_int >= 1:
            return False

        return True

    @classmethod
    def take(cls, keyring, array):
        """Retrieve part of an array.

        Amounts to `return array[keyring]`.
       
        Uses numpy normal indexing when possible.
        If not, uses more complex method to access array.

        Parameters
        ----------
        keyring: Keyring
            Part of the array to take.
        array: Array

        Returns
        -------
        Array
            View of the input array in the case
            of normal indexing, or a copy otherwise.

        Notes
        -----
        See :doc:`../accessor` for more information.

        See Numpy docpage on indexing
        https://docs.scipy.org/doc/numpy/user/basics.indexing.html

        See also
        --------
        take_normal:
             Function used for normal indexing.
        take_complex:
             Function used when normal indexing
             would not work.
        """
        if cls.has_normal_access(keyring):
            return cls.take_normal(keyring, array)
        return cls.take_complex(keyring, array)

    @classmethod
    def take_normal(cls, keyring, array):
        """Retrieve part of an array with normal indexing.

        Amounts to `array[keyring]`.
        Returns a view into the array.

        Parameters
        ----------
        keyring: Keyring
            Part of the array to take.
        array: Array

        Returns
        -------
        Array
        """
        cls.check_dim(keyring, array)
        return array[tuple(keyring.keys_values)]

    @classmethod
    def take_complex(cls, keyring, array):
        """Retrieve part of an array without normal indexing.

        Amounts to `array[keyring]`.
        Returns a copy of the array.

        Parameters
        ----------
        keyring: Keyring
            Part of the array to take.
        array: Array

        Returns
        -------
        Array
        """
        cls.check_dim(keyring, array)

        out = array
        keys = []
        for k in keyring.keys:
            keys_ = tuple(keys + [k.value])
            out = out[keys_]
            if k.shape != 0:
                keys.append(slice(None, None))
        return out

    @classmethod
    def place(cls, keyring, array, chunk):
        """Assign a part of array with another array.

        Amounts to `array[keyring] = chunk`.
        Uses numpy normal indexing when possible.
        If not, uses more complex method to access array.

        Parameters
        ----------
        keyring: Keyring
            Part of array to assign.
        array: Array
            Array to assign.
        chunk: Array
            Array to be assigned.

        See also
        --------
        take:
             Function to access part of array, with more
             details on normal and complexed indexing.
        """
        if cls.has_normal_access(keyring):
            cls.place_normal(keyring, array, chunk)
        else:
            cls.place_complex(keyring, array, chunk)

    @classmethod
    def place_normal(cls, keyring, array, chunk):
        """Assign a part of an array with normal indexing.

        Amounts to `array[keyring] = chunk`.
        Uses numpy normal indexing when possible.
        If not, uses more complex method to access array.

        Parameters
        ----------
        keyring: Keyring
            Part of array to assign.
        array: Array
            Array to assign.
        chunk: Array
            Array to be assigned.
       """
        cls.check_shape(keyring, chunk)
        array[tuple(keyring.keys_values)] = chunk

    @classmethod
    def place_complex(cls, keyring, array, chunk):
        """Assign part of an array without normal indexing.

        Amounts to `array[keyring] = chunk`.
        Uses numpy normal indexing when possible.
        If not, uses more complex method to access array.

        Parameters
        ----------
        keyring: Keyring
            Part of array to assign.
        array: Array
            Array to assign.
        chunk: Array
            Array to be assigned.
        """
        raise NotImplementedError

    @staticmethod
    def moveaxis(array, source, destination):
        """Exchange axes.

        Parameters
        ----------
        array: Array
        source: List[int]
            Original position of axes to move.
        destination: List[int]
            Destination positions of axes to move.

        Returns
        -------
        Array

        See also
        --------
        numpy.moveaxis: Function used.
        """
        out = np.moveaxis(array, source, destination)
        return out

    @classmethod
    def reorder(cls, keyring, array, order):
        """Reorder array dimensions.

        Parameters
        ----------
        keyring: Keyring
            Keyring used to take the array.
            Defines the dimensions names.
        array: Array
        order: List[str]
            Target dimensions order.
            Not all dimensions names need to be specified,
            but all dimensions specified must be in the
            array (ie be in the keyring, with a shape above 0).

        Returns
        -------
        Array
        """
        # TODO: add securities
        # Current data order
        current = keyring.get_non_zeros()
        source = [current.index(n) for n in current if n in order]
        dest = [current.index(n) for n in order]
        if source != dest:
            return cls.moveaxis(array, source, dest)
        return array

    @staticmethod
    def concatenate(arrays, axis=0, out=None):
        """Concatenate arrays.

        Parameters
        ----------
        array: List[Array]
            Arrays to concatenate.
        axis: int, optional
            The axis along which the arrays will be joined.
            If None, the arrays are flattened.
        out: Array, optional
            Array to place the result in.

        Returns
        -------
        Array

        See also
        --------
        numpy.concatenate: Function used.
        """
        return np.concatenate(arrays, axis=axis, out=out)
