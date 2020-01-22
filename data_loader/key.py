"""Object for indexing the data array."""

import numpy as np


class Key():
    """Element for indexing a dimension of an array.

    Can be None, int, List[int] or slice.

    Parameters
    ----------
    key: None, int, List[int], slice
        Key-like object.

    Attributes
    ----------
    value: None, int, List[int], slice
    type: str
        {'none', 'int', 'list', 'slice'}
    """

    int_types = (int, np.integer)

    def __init__(self, key):
        reject = False
        if isinstance(key, (list, tuple, np.ndarray)):
            reject = not all(isinstance(z, self.int_types) for z in key)
            tp = 'list'
            key = [int(z) for z in key]
        elif isinstance(key, self.int_types):
            tp = 'int'
            key = int(key)
        elif isinstance(key, slice):
            tp = 'slice'
        elif key is None:
            tp = 'none'
        else:
            reject = True
        if reject:
            raise TypeError("Key is not int, List[int], or slice"
                            " (is %s)" % type(key))
        self.value = key
        self.type = tp
        self.set_shape()

    def __eq__(self, other):
        return self.value == other.value

    def __str__(self):
        return str(self.value)


    def set_shape(self):
        """Set shape if possible.

        Set the shape attribute.
        Shape is the size a array would have
        if the key was applied.

        Is None if cannot be determined.
        """
        if self.type == 'int':
            self.shape = 0
        elif self.type == 'list':
            self.shape = len(self.value)
        else:
            self.shape = None

    def set_shape_coord(self, coord):
        """Set shape using a coordinate.

        Parameters
        ----------
        coord: Coord
            The coordinate that would be used.
        """
        self.shape = coord[self.value].size

    def no_int(self):
        """Return value, replaces int with list."""
        if self.type == 'int':
            return [self.value]
        return self.value

    def reverse(self, size):
        """Reverse key.

        Parameters
        ----------
        size: int
            Size of the coordinate.
        """
        if self.type == 'int':
            self.value = size - self.value
        elif self.type == 'list':
            self.value = [size - z for z in self.value]
        elif self.type == 'slice':
            self.value = reverse_slice(self.value, size)

    def simplify(self):
        """Simplify list into a list.

        Transform a list into a slice if the list is
        a serie of integers of fixed step.
        """
        if self.type == 'list':
            key = list2slice_simple(self.value)
            if isinstance(key, slice):
                self.type = 'slice'
            self.value = key


class Keyring():
    """Object for indexing an array.

    Multiple coordinates can be specified.

    Parameters
    ----------
    keys: Key or int or List[int] or slice
        What part of the data must be selected
        for a given coordinate.

    Attributes
    ----------
    _keys: Dict[Key]
    """
    def __init__(self, **keys):
        self._keys = {}

        for name, key in keys.items():
            self[name] = key

    def __getitem__(self, item):
        """Return key for a coordinate.

        Parameters
        ----------
        item: str
            Coordinate name.
        """
        return self._keys[item]

    def __setitem__(self, item, value):
        """Set item.

        Parameters
        ----------
        item: str
            Coordinate name
        value: Key or key-like
        """
        if not isinstance(value, Key):
            value = Key(value)
        self._keys[item] = value

    def __iter__(self):
        return iter(self._keys)

    def __len__(self):
        return len(self._keys)

    @property
    def coords(self):
        """List of coordinates present in the keyring.

        Returns
        -------
        List[str]
        """
        return list(self._keys.keys())

    @property
    def keys(self):
        """List of keys present in the keyring.

        Returns
        -------
        List[Key]
        """
        return list(self._keys.values())

    @property
    def keys_values(self):
        """List of keys values present in the keyring.

        Returns
        -------
        List[key-like]
        """
        return [k.value for k in self.keys]

    @property
    def kw(self):
        """Return dictionary of keys values."""
        return dict(zip(self.coords, self.keys_values))

    @property
    def shape(self):
        """Return shape of all keys."""
        return [k.shape for k in self.keys]

    def subset(self, coords):
        """Return a subpart of this keyring.

        Parameters
        ----------
        coords: List[str]
        """
        return Keyring(**{c: self[c] for c in coords})

    def items(self):
        """Iterate through coordinates and keys.

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

    def __str__(self):
        s = []
        for c, key in self.items():
            s.append('%s: %s' % (c, str(key)))
        return str(', '.join(s))


    def set_shape(self, coords):
        """Set shape of all keys using coordinates.

        Parameters
        ----------
        coords: Dict[Coord]
        """
        for name, c in coords.items():
            self[name].set_shape_coord(c)

    def get_non_zeros(self):
        """Return coordinates with a non zero shape.

        ie whose dimension would not be squeezed.
        """
        return [name for name, k in self.items()
                if k.shape is None or k.shape > 0]

    def sort_by(self, order):
        """Sort keys by order.

        Parameters
        ----------
        order: List[str]
             Coordinates present in the keyring.
        """
        if len(order) < len(self.keys):
            raise IndexError("Order given is too short.")

        keys_ord = {}
        for name in order:
            keys_ord[name] = self[name]
        self._keys = keys_ord

    def make_full(self, coords, fill=None):
        """Fill keyring missing coords.

        Parameters
        ----------
        coords: List[str]
        fill: Any
        """
        for c in coords:
            if c not in self:
                self[c] = fill

    def make_total(self, *coords, miss=None):
        """Fill missing keys by total slices.

        Parameters
        ----------
        coords: str
        miss: Any
        """
        if not coords:
            coords = self.coords
        for c, v in self.items_values():
            if c in coords and v == miss:
                self[c] = slice(None, None)

    def make_single(self, *coords, idx=0, miss=None):
        """Fill missing keys by an index.

        Parameters
        ----------
        coords: str
        idx: int
        miss: Any
        """
        if not coords:
            coords = self.coords
        for c, v in self.items_values():
            if c in coords and v == miss:
                self[c] = idx

    def make_int_list(self, *coords):
        """Turn integer values into lists.

        Parameters
        ----------
        coords: str
        """
        if not coords:
            coords = self.coords
        for c, k in self.items():
            if c in coords and k.type == 'int':
                self[c] = [k.value]

    def get_high_dim(self):
        """Returns coordinates of size higher than one."""
        out = [c for c, k in self.items()
               if k.shape is None or k.shape > 1]
        return out

    def simplify(self):
        """Simplify keys."""
        for key in self.keys:
            key.simplify()


def list2slice_simple(L):
    """Transform a list into a slice when possible.

    Step can be any integer.
    Can be descending.
    """
    if len(L) < 2:
        return L

    diff = np.diff(L)
    if len(L) == 2:
        diff2 = np.array([0])
    else:
        diff2 = np.diff(diff)

    if np.all(diff2 == 0):
        step = diff[0]
        start = L[0]
        stop = L[-1] + step

        if stop < 0:
            stop = None
        L = slice(start, stop, step)

    return L


def list2slice_complex(L):
    """Transform a list of integer into a list of slices.

    Find all series of continuous integer with a fixed
    step (that can be any integer) of length greater than 3.

    Examples
    --------
    [0, 1, 2, 3, 7, 8, 9, 10, 16, 14, 12, 10, 3, 10, 11, 12]
    will yield:
    [slice(0, 4, 1), slice(8, 11, 1), slice(16, 9, -2), 3, slice(10, 13, 1)]
    """
    if len(L) < 3:
        return L

    diff = list(np.diff(L))
    diff2 = np.diff(diff)

    # Index of separation between two linear parts
    sep = np.where(diff2 != 0)[0]
    # Only one of the index (this is a second derivative of a step function)
    sep_start = sep[np.where(np.diff(sep) == 1)[0]] + 2

    idx = list(sep_start)
    if diff[0] != diff[1]:
        idx.insert(0, 1)
    if diff[-1] != diff[-2]:
        idx.append(len(L)-1)
        diff.append(diff[-1]+1)

    idx.insert(0, 0)
    idx.append(len(L))

    slices = []
    for i in range(len(idx)-1):
        i1 = idx[i]
        i2 = idx[i+1]
        start = L[i1]

        if i2 - i1 == 1:
            slices.append([start])
            continue

        step = diff[i1]
        stop = L[i2-1] + 1

        if step < 0:
            stop -= 2
            if stop == -1:
                stop = None

        slc = slice(start, stop, step)
        slices.append(slc)

    return slices


def simplify_key(key):
    """Simplify a key.

    Transform a list into a slice if the list is
    a serie of integers of fixed step.
    """
    if isinstance(key, (list, tuple, np.ndarray)):
        key = list2slice_simple(list(key))
    return key


def reverse_slice(sl, size=None):
    """Reverse a slice.

    Parameters
    ----------
    sl: Slice
        Slice to reverse.
    size: int, optional
        Size of the list to get indices from.
    """
    if size is None:
        size = sl.stop - sl.start

    ind = sl.indices(size)
    shift = [-1, 1][ind[2] < 0]

    start = ind[1] + shift
    stop = ind[0] + shift
    step = -ind[2]

    if stop == -1:
        stop = None

    return slice(start, stop, step)