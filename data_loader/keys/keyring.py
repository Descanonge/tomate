"""Keyring regrouping multiple keys."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


import logging
from typing import List

import numpy as np

from data_loader.keys.key import Key, KeyVar


log = logging.getLogger(__name__)



class Keyring():
    """Object for indexing an array.

    Multiple dimensions can be specified.

    See :doc:`../accessor` for more information.

    Parameters
    ----------
    keys: Key-like
        What part of the data must be selected
        for a given dimension.
    """

    @classmethod
    def get_default(cls, keyring=None, variables=None, **keys) -> "Keyring":
        """Return a new keyring, eventually updated.

        Parameters
        ----------
        keyring: Keyring, optional
            Keyring to take values from.
        keys: Key, Key-like
            Keys to add to the keyring.
        """
        if keyring is None:
            keyring = cls()
        else:
            keyring = keyring.copy()
        keyring.update(keys)

        if variables is not None:
            keyring.make_var_idx(variables)

        return keyring

    def __init__(self, **keys):
        self._keys = {}

        for name, key in keys.items():
            self[name] = key

    def __getitem__(self, item) -> Key:
        """Return key for a dimension.

        Parameters
        ----------
        item: str
            Dimension name.
        """
        return self._keys[item]

    def __setitem__(self, item, value):
        """Set key value to dimension.

        Parameters
        ----------
        item: str
            Dimension name
        value: Key, key-like
        """
        if not isinstance(value, Key):
            if item == 'var':
                value = KeyVar(value)
            else:
                value = Key(value)
        self._keys[item] = value

    def __iter__(self):
        """Returns dict iterator over dimensions names."""
        return iter(self._keys)

    def __len__(self) -> int:
        """Returns number of dimensions."""
        return len(self._keys)

    @property
    def dims(self) -> List[str]:
        """List of dimensions present in the keyring."""
        return list(self._keys.keys())

    @property
    def keys(self) -> List[Key]:
        """List of keys present in the keyring."""
        return list(self._keys.values())

    @property
    def keys_values(self):
        """List of keys values present in the keyring.

        Returns
        -------
        List[Key-like]
        """
        return [k.value for k in self.keys]

    @property
    def kw(self):
        """Return dictionary of keys values.

        Returns
        -------
        Dict[str, Key-like]
        """
        return dict(zip(self.dims, self.keys_values))

    @property
    def shape(self) -> List[int]:
        """Return shape of all keys."""
        return [k.shape for k in self.keys if k.shape != 0]

    def __bool__(self):
        """If the keyring has keys."""
        return len(self.dims) > 0

    def subset(self, dims):
        """Return a subcopy of this keyring.

        Parameters
        ----------
        dims: List[str]

        Returns
        -------
        Keyring
             Keyring with only specified keys.
        """
        return Keyring(**{c: self[c] for c in dims})

    def items(self):
        """Iterate through dimensions and keys.

        Returns
        -------
        Dict_item(List[str], List[Key])
        """
        return self._keys.items()

    def items_values(self):
        """List of keys values present in the keyring.

        Returns
        -------
        Dict_item(List[str], List[key-like]])
        """
        d = {name: key.value for name, key in self.items()}
        return d.items()

    def update(self, keys):
        """Update keyring.

        Parameters
        ----------
        keys: Dict[Key or key-like]
        """
        for name, key in keys.items():
            self[name] = key

    def pop(self, dim: str) -> Key:
        """Pop a key."""
        return self._keys.pop(dim)

    def __str__(self):
        s = []
        for c, key in self.items():
            s.append('%s: %s' % (c, str(key)))
        return str(', '.join(s))

    def __repr__(self):
        return '\n'.join([super().__repr__(), str(self)])

    def copy(self) -> "Keyring":
        """Return copy of self."""
        args = {c: k.copy() for c, k in self.items()}
        keyring = Keyring(**args)
        return keyring

    def set_shape(self, coords):
        """Set shape of all keys using coordinates.

        Parameters
        ----------
        coords: Dict[Coord]
        """
        for name, k in self.items():
            k.set_shape_coord(coords[name])

    def get_non_zeros(self) -> List[str]:
        """Return dimensions name with a non zero shape.

        ie whose dimension would not be squeezed.
        """
        return [name for name, k in self.items()
                if k.shape is None or k.shape > 0]

    def sort_by(self, order):
        """Sort keys by order.

        Parameters
        ----------
        order: List[str]
             Dimensions present in the keyring.
        """
        if len(order) < len(self.keys):
            raise IndexError("Order given is too short.")

        keys_ord = {}
        for name in order:
            keys_ord[name] = self[name]
        self._keys = keys_ord

    def check_unwanted(self, dims):
        """Check if keyring contains unwanted dimensions."""
        for c in self:
            if c not in dims:
                raise KeyError("'%s' dimension is unwanted in keyring." % c)

    def make_full(self, dims, fill=None):
        """Add dimensions.

        Parameters
        ----------
        dimensions: List[str]
            List of dimensions to add if not
            already present.
        fill: Any, optional
            Value to set new keys to.
        """
        for c in self:
            if c not in dims:
                log.warning("'%s' dimension in keyring is not in specified "
                            "full list of dimensions, and might be unwanted.", c)
        for c in dims:
            if c not in self:
                self[c] = fill

    def make_total(self, *dims):
        """Fill missing keys by total slices.

        Parameters
        ----------
        dims: str, optional
            Dimensions names to fill if missing.
            If not specified, all are selected.
        """
        if not dims:
            dims = self.dims
        for c, k in self.items():
            if c in dims and k.type == 'none':
                self[c] = slice(None, None)

    def make_single(self, *dims, idx=0):
        """Fill missing keys by an index.

        Parameters
        ----------
        dims: str, optional
            Dimensions names to fill if missing.
            If not specified, all are selected.
        idx: int, optional
            Index to set as value.
        """
        if not dims:
            dims = self.dims
        for c, k in self.items():
            if c in dims and k.type == 'none':
                self[c] = idx

    def make_int_list(self, *dims):
        """Turn integer values into lists.

        Parameters
        ----------
        dims: str
             Dimensions names to change if
             necessary. If not specified, all are
             selected.
        """
        if not dims:
            dims = self.dims
        for c, k in self.items():
            if c in dims and k.type == 'int':
                self[c].make_int_list()

    def make_list_int(self, *dims):
        """Turn lists of length one in integers.

        Parameters
        ----------
        dims: str
             Dimensions names to change if
             necessary. If not specified, all are
             selected.
        """
        if not dims:
            dims = self.dims
        for c, k in self.items():
            if c in dims:
                k.make_list_int()

    def make_idx_var(self, variables):
        """Transform indices into variables names.

        Parameters
        ----------
        variables: Variables
        """
        if 'var' in self:
            self['var'].make_idx_var(variables)

    def make_var_idx(self, variables):
        """Transform variables names into indices.

        Parameters
        ----------
        variables: Variables
        """
        if 'var' in self:
            self['var'].make_var_idx(variables)

    def get_high_dim(self) -> List[str]:
        """Returns coordinates of size higher than one."""
        out = [c for c, k in self.items()
               if k.shape is None or k.shape > 1]
        return out

    def simplify(self):
        """Simplify keys.

        Turn list into a slice if possible.
        """
        for key in self.keys:
            key.simplify()

    def sort_keys(self, *dims):
        """Sort keys.

        Remove redondant indices.
        Sort by indices.
        """
        if dims is None:
            dims = self.dims
        for d in self.keys:
            d.sort()

    def __mul__(self, other):
        """Subset keyring by another.

        If `B = A[self]`
        and `C = B[other]`
        then `C = A[self*other]`

        Parameters
        ----------
        other: Keyring

        Returns
        -------
        Keyring
            self*other
        """
        res = Keyring()
        other_ = other.copy()
        other_.make_full(self.dims)
        other_.make_total()
        for name, key in self.items():
            res[name] = key * other_[name]
        return res

    def __add__(self, other):
        """Expand keyring with another."""
        res = self.copy()
        for d in other:
            if d in self:
                res[d] = self[d] + other[d]
            else:
                res[d] = other[d]
        return res

    def is_shape_equivalent(self, other):
        """Compare keyrings shapes.

        Parameters
        ----------
        other: Keyring, Sequence[int, None]
        """
        if isinstance(other, type(self)):
            other = other.shape
        else:
            other = list(other)

        if len(self.shape) == len(other) == 0:
            out = True
        else:
            out = any(a is None
                      or b is None
                      or a == b
                      for a, b in zip(self.shape, other))
        return out

    def print(self) -> str:
        """Return readable concise string representation."""
        s = []
        for k in self.keys:
            if k.type == 'int':
                s.append(str(k.value))
            elif k.type == 'list':
                if len(k.value) <= 5:
                    s.append(str(k.value))
                else:
                    z = '[%s, %s, ..., %s, %s]' % (*k.value[:2], *k.value[-2:])
                    s.append(z)
            elif k.type == 'slice':
                z = []
                start, stop, step = k.value.start, k.value.stop, k.value.step
                if start is None:
                    z.append('')
                else:
                    z.append(str(start))
                if stop is None:
                    z.append('')
                else:
                    z.append(str(stop))
                if step is not None and step != 1:
                    z.append(str(step))
                s.append(':'.join(z))
        return '[%s]' % ', '.join(s)

