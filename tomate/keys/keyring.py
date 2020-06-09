"""Keyring regrouping multiple keys."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import logging
from typing import (Any, Dict, Iterator, Iterable, List,
                    Optional, Tuple, Union, TYPE_CHECKING)

from tomate.keys.key import Key, KeyVar

from tomate.custom_types import KeyLike

if TYPE_CHECKING:
    from tomate.coordinates.coord import Coord
    from tomate.coordinates.variables import Variables

log = logging.getLogger(__name__)


class Keyring():
    """Object for indexing an array.

    Multiple dimensions can be specified.

    See :doc:`../accessor` for more information.

    :param keys: What part of the data must be selected
        for a given dimension.
    """

    @classmethod
    def get_default(cls, keyring: 'Keyring' = None,
                    variables: 'Variables' = None,
                    **keys: KeyLike) -> 'Keyring':
        """Return a new keyring, eventually updated.

        :param keyring: Keyring to take values from.
        :param keys: Keys to add to the keyring.
        """
        if keyring is None:
            keyring = cls()
        else:
            keyring = keyring.copy()
        keyring.update(keys)

        if variables is not None:
            if not variables.has_data():
                raise ValueError("Variables dimension is empty.")
            keyring.make_var_idx(variables)

        return keyring

    def __init__(self, **keys: Union[Key, KeyLike]):
        self._keys = {}

        for name, key in keys.items():
            self[name] = key

    def __getitem__(self, item: str) -> Key:
        """Return key for a dimension.

        :param item: Dimension name.
        """
        try:
            return self._keys[item]
        except KeyError:
            raise KeyError(f"'{item}' not in keyring.")

    def __setitem__(self, item: str, value: Union[Key, KeyLike]):
        """Set key value to dimension.

        :param item: str: Dimension name
        """
        if not isinstance(value, Key):
            if item == 'var':
                value = KeyVar(value)
            else:
                value = Key(value)
        self._keys[item] = value

    def __iter__(self) -> Iterator[str]:
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
    def keys_values(self) -> List[KeyLike]:
        """List of keys values present in the keyring."""
        return [k.value for k in self.keys]

    @property
    def kw(self) -> Dict[str, KeyLike]:
        """Return dictionary of keys values."""
        return dict(zip(self.dims, self.keys_values))

    @property
    def shape(self) -> List[int]:
        """Return shape of all keys."""
        return [k.shape for k in self.keys if k.shape != 0]

    def __bool__(self):
        """If the keyring has keys."""
        return len(self.dims) > 0

    def subset(self, dims: List[str]) -> 'Keyring':
        """Return a subcopy of this keyring.

        :returns: Keyring with only specified keys.
        """
        return Keyring(**{c: self[c] for c in dims})

    def items(self) -> Iterator[Tuple[str, Key]]:
        """Iterate through dimensions and keys."""
        return self._keys.items()

    def items_values(self) -> Iterator[Tuple[str, KeyLike]]:
        """List of keys values present in the keyring."""
        d = {name: key.value for name, key in self.items()}
        return d.items()

    def update(self, keys: Dict[str, Union[Key, KeyLike]]):
        """Update keyring."""
        for name, key in keys.items():
            self[name] = key

    def pop(self, dim: str) -> Key:
        """Pop a key."""
        return self._keys.pop(dim)

    def __repr__(self):
        s = []
        for c, key in self.items():
            s.append('%s: %s' % (c, str(key)))
        return str(', '.join(s))

    def copy(self) -> 'Keyring':
        """Return copy of self."""
        args = {c: k.copy() for c, k in self.items()}
        keyring = Keyring(**args)
        return keyring

    def set_shape(self, coords: Dict[str, 'Coord']):
        """Set shape of keys using coordinates."""
        for name, k in self.items():
            if name in coords:
                k.set_shape_coord(coords[name])

    def get_non_zeros(self) -> List[str]:
        """Return dimensions name with a non zero shape.

        ie whose dimension would not be squeezed.
        """
        return [name for name, k in self.items()
                if k.shape is None or k.shape > 0]

    def sort_by(self, order: List[str]):
        """Sort keys by order.

        :param order: Dimensions present in the keyring.
        :raises IndexError: Order shorter then keyring, does
            not allow to sort unambiguously.
        """
        if len(order) < len(self.keys):
            raise IndexError("Order given is too short.")

        keys_ord = {}
        for name in order:
            keys_ord[name] = self[name]
        self._keys = keys_ord

    def check_unwanted(self, dims: List[str]):
        """Check if keyring contains unwanted dimensions.

        :raises KeyError: Dimension is present in keyring but not `dims`.
        """
        for c in self:
            if c not in dims:
                raise KeyError(f"'{c}' dimension is unwanted in keyring.")

    def make_full(self, dims: List[str], fill: Any = None):
        """Add dimensions.

        :param dimensions: List of dimensions to add if not
            already present.
        :param fill: [opt] Value to set new keys to.
        """
        for c in self:
            if c not in dims:
                log.warning("'%s' dimension in keyring is not in specified "
                            "full list of dimensions, and might be unwanted.", c)
        for c in dims:
            if c not in self:
                self[c] = fill

    def make_total(self, *dims: str):
        """Fill missing keys by total slices.

        :param dims: [opt] Dimensions names to fill if missing.
            If not specified, all are selected.
        """
        if not dims:
            dims = self.dims
        for dim, k in self.items():
            if dim in dims and k.type == 'none':
                k.set(slice(None, None))

    def make_single(self, *dims: str, idx: Union[Key, KeyLike] = 0):
        """Fill missing keys by an index.

        :param dims: Dimensions names to fill if missing.
            If not specified, all are selected.
        :param idx: Index to set as value.
        """
        if not dims:
            dims = self.dims
        for c, k in self.items():
            if c in dims and k.type == 'none':
                self[c] = idx

    def make_int_list(self, *dims: str):
        """Turn integer values into lists.

        :param dims: [opt] Dimensions names to change if
             necessary. If not specified, all are
             selected.
        """
        if not dims:
            dims = self.dims
        for c, k in self.items():
            if c in dims and k.type == 'int':
                self[c].make_int_list()

    def make_list_int(self, *dims: str):
        """Turn lists of length one in integers.

        :param dims: Dimensions names to change if
             necessary. If not specified, all are
             selected.
        """
        if not dims:
            dims = self.dims
        for c, k in self.items():
            if c in dims:
                k.make_list_int()

    def make_idx_var(self, variables: 'Variables'):
        """Transform indices into variables names."""
        if 'var' in self:
            self['var'].make_idx_var(variables)

    def make_var_idx(self, variables: 'Variables'):
        """Transform variables names into indices."""
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

    def sort_keys(self, *dims: str):
        """Sort keys.

        Remove redondant indices.
        Sort by indices.
        """
        if dims is None:
            dims = self.dims
        for d in self.keys:
            d.sort()

    def __mul__(self, other: 'Keyring') -> 'Keyring':
        """Subset keyring by another.

        If `B = A[self]`
        and `C = B[other]`
        then `C = A[self*other]`

        :returns: self*other
        """
        res = Keyring()
        other_ = other.copy()
        other_.make_full(self.dims)
        other_.make_total()
        for name, key in self.items():
            res[name] = key * other_[name]
        return res

    def __add__(self, other: 'Keyring') -> 'Keyring':
        """Expand keyring with another."""
        res = self.copy()
        for d in other:
            if d in self:
                res[d] = self[d] + other[d]
            else:
                res[d] = other[d]
        return res

    def is_shape_equivalent(self, other: Union[Iterable[Optional[int]],
                                               'Keyring']) -> bool:
        """Compare keyrings shapes."""
        if isinstance(other, type(self)):
            other = other.shape
        else:
            other = list(other)

        if len(self.shape) == len(other) == 0:
            out = True
        else:
            out = all([a is None
                       or b is None
                       or a == b
                       for a, b in zip(self.shape, other)])
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
                    z = '[{}, {}, ..., {}, {}]'.format(*k.value[:2], *k.value[-2:])
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
        return f"[{', '.join(s)}]"
