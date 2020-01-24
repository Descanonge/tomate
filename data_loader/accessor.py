"""Manages access to data array."""


import logging

import numpy as np


log = logging.getLogger(__name__)


class Accessor():
    """Manages access to arrays.

    Stores static and class methods.
    """

    @staticmethod
    def ndim(array):
        """Return number of dimensions of array.

        Returns
        -------
        int
        """
        return array.ndim

    @staticmethod
    def shape(array):
        """Return shape of array.

        Returns
        -------
        List[int]
        """
        return list(array.shape)

    @classmethod
    def check_dim(cls, keyring, array):
        """Check if keyring match array rank.

        Parameters
        ----------
        keyring: Keyring or Dict or List
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
        array: Array
        """
        if any(k is not None and a != k
                for a, k in zip(cls.shape(array), keyring.shape)):
            raise ValueError("Mismatch between selected data "
                             "and keyring shape (array: %s, keyring: %s)"
                             % (cls.shape(array), keyring.shape))

    @classmethod
    def has_normal_access(cls, keyring):
        """Check if keyring would need complex access."""
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

        return array[keyring]

        Parameters
        ----------
        keyring: Keyring
            Part of the array to take.
        array: Array

        Returns
        -------
        Array
        """
        if cls.has_normal_access(keyring):
            return cls.take_normal(keyring, array)
        return cls.take_complex(keyring, array)

    @classmethod
    def take_normal(cls, keyring, array):
        """Retrieve part of an array with normal indexing.

        Returns a view into the array.
        return array[keyring]

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

        Returns a copy of the array.
        return array[keyring]

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
        """Assign part of an array with another.

        Array[keyring] = chunk

        Parameters
        ----------
        keyring: Keyring
            Tell part of array to assign.
        array: Array
            Array to assign
        chunk: Array
            Array to be assigned
        """
        if cls.has_normal_access(keyring):
            cls.place_normal(keyring, array, chunk)
        else:
            cls.place_complex(keyring, array, chunk)

    @classmethod
    def place_normal(cls, keyring, array, chunk):
        """Assign part of an array with normal indexing.

        Array[keyring] = chunk

        Parameters
        ----------
        keyring: Keyring
            Tell part of array to assign.
        array: Array
            Array to assign
        chunk: Array
            Array to be assigned
       """
        cls.check_shape(keyring, chunk)
        array[tuple(keyring.keys_values)] = chunk

    @classmethod
    def place_complex(cls, keyring, array, chunk):
        """Assign part of an array without normal indexing.

        Array[keyring] = chunk

        Parameters
        ----------
        keyring: Keyring
            Tell part of array to assign.
        array: Array
            Array to assign
        chunk: Array
            Array to be assigned
        """
        raise NotImplementedError

    @staticmethod
    def moveaxis(array, source, destination):
        """Exchange axis.

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
        """
        out = np.moveaxis(array, source, destination)
        return out

    @staticmethod
    def get_order_arg(current, order):
        """Return indexing needed to exchange axis.

        Parameters
        ----------
        current: List[str]
            Current dimension names.
        order: List[str]
            Target dimensions order.

        Returns
        -------
        List[int]
            Sources indices.
        List[int]
            Destination indices.
        """
        source = list(range(len(current)))
        dest = [current.index(n) for n in order]

        source_, dest_ = [], []
        for s, d in zip(source, dest):
            if s != d:
                source_.append(s)
                dest_.append(d)
        return source, dest

    @classmethod
    def reorder(cls, keyring, array, order):
        """Reorder array dimensions.

        Parameters
        ----------
        keyring: Keyring
            Keyring used to take the array.
        array: Array
        order: List[str]
            Target dimensions order.

        Returns
        -------
        Array
        """
        # TODO: add securities
        non_zeros = keyring.get_non_zeros()
        source, dest = cls.get_order_arg(non_zeros, order)
        return cls.moveaxis(array, source, dest)

    @staticmethod
    def concatenate(arrays, *args, **kwargs):
        """Concatenate arrays.

        Parameters
        ----------
        array: List[Array]
        args, kwargs:
            Passed to np.concatenate.

        Returns
        -------
        Array
        """
        return np.concatenate(arrays, *args, **kwargs)
