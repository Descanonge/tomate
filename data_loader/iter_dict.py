"""Indexed (and ordered) dictionnary.

An IterDict instance can be accessed with
a string or iterable of string, an integer
index, list or slice

Uses python 3.7 ordered dictionnary feature.
"""

import sys

if sys.version_info[:2] < (3, 7):
    raise Exception("Python 3.7 or a more recent version is required.")
    # After python 3.7 dictionnaries are guaranteed to conserve the order of
    #  item assignement. Dict containing infos associated with variables names
    #  are kept in sync with data array.
    # BUT the code has been written so that this is uncessary, however this
    #  presently still need reviewing.


class IterDict(dict):
    """Dictionnary that can also be indexed (and sliced).

    Created as a typical dictionnary. The order the
    items are initialized will be kept.

    Methods
    -------

    enum
        Enumerate values

    __getitem__
        Return value from a string or an integer
    """

    def __getitem__(self, y):
        """Return value.

        Parameters
        ----------
        y: int, str, slice, List[int], List[str]
            key

        Notes
        -----
        For index and slices, python3.7 ordered dict abalities are used
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
