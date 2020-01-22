"""Indexed (and ordered) dictionnary.

An IterDict instance can be accessed with
a string or iterable of string, an integer
index, list or slice

Uses python 3.7 ordered dictionnary feature.
"""

import sys


class IterDict(dict):
    """Dictionnary that can also be indexed (and sliced).

    Created as a typical dictionnary. The order the
    items are initialized in will be kept.

    Methods
    -------
    __getitem__
        Retrieve elements from its key or index.
    """

    def __getitem__(self, y):
        """Return value.

        Parameters
        ----------
        y: int, str, slice, List[int], List[str]
            key

        Notes
        -----
        For index and slices, python3.7 ordered dict abilities are used

        Examples
        --------
        >>> ID = IterDict({'a': 'A', 'b': 'B', 'c': 'C'})
        ... print(ID['a'])
        'A'
        >>> print(ID[0])
        'A'
        >>> print(ID[1:])
        ['B', 'C']
        """

        getitem = super().__getitem__

        def get(i):
            """For a single object."""
            if isinstance(i, str):
                return getitem(i)
            if isinstance(i, int):
                return list(self.values())[i]
            return None

        if isinstance(y, slice):
            start, stop, step = y.start, y.stop, y.step
            if isinstance(start, str):
                start = list(self.keys()).index(start)
            if isinstance(stop, str):
                stop = list(self.keys()).index(stop)

            y = list(range(*slice(start, stop, step).indices(len(self))))

        if isinstance(y, (list, tuple)):
            res = []
            for i in y:
                res.append(get(i))
            return res

        return get(y)

    def enum(self):
        """Enumerate values."""
        return enumerate(self.values())
