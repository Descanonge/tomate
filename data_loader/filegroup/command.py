"""Command for loading data.

Contains
--------
Key:
    Key for taking a slice of data and putting somewhere.

Command:
    A command to indicate what to load and how.
"""

import os
import logging

import numpy as np


log = logging.getLogger(__name__)


class Key():
    """Key used in a Command.

    Parameters
    ----------
    infile: Dict of keys {coord name: key}
        Keys that will be taken in file
    memory: Dict of keys {coord name: key}
        Keys to indicate where to put the data
        in the memory.

    Attributes
    ----------
    infile: Dict of keys {coord name: key}
        Keys that will be taken in file
    memory: Dict of keys {coord name: key}
        Keys to indicate where to put the data
        in the memory.
    """

    def __init__(self, infile=None, memory=None):
        if infile is None:
            infile = {}
        if memory is None:
            memory = {}
        self.infile = infile
        self.memory = memory

    def __str__(self):
        return 'in-file: ' + str(self.infile) + ' | memory: ' + str(self.memory)

    def __iter__(self):
        return iter([self.infile, self.memory])

    def __getitem__(self, key):
        return [self.infile[key], self.memory[key]]

    def set(self, infile, memory):
        """Set keys."""
        self.infile = infile
        self.memory = memory

    def modify(self, infile=None, memory=None):
        """Modify keys in place."""
        if infile is not None:
            self.infile.update(infile)
        if memory is not None:
            self.memory.update(memory)


class Command():
    """Information for loading slices of data.

    Attributes
    ----------
    filename: str
        File to open
    var_list: List of str
        Variables to take in that file.
    keys: List of Keys
        List of Keys objects to take in that file.
    """

    def __init__(self):
        self.filename = ""
        self.var_list = []
        self.keys = []

    def __iter__(self):
        """Iter on keys."""
        return iter(self.keys)

    def __str__(self):
        s = []
        s.append("file: %s" % self.filename)
        if self.var_list:
            s.append("variables: " + str(self.var_list))
        s.append("keys: %s" % '\n      '.join([str(k) for k in self]))
        return "\n".join(s)

    def __len__(self):
        return len(self.keys)

    def __getitem__(self, i):
        return self.keys[i]

    def __iadd__(self, other):
        """."""
        for k in other:
            self.append(*k)
        return self

    def append(self, key_infile, key_memory):
        """Add key."""
        self.keys.append(Key(key_infile, key_memory))

    def add_keys(self, keys_infile, keys_memory):
        """Add keys."""
        n = len(keys_infile)
        for i in range(n):
            self.append(keys_infile[i], keys_memory[i])

    def set_key(self, key_infile, key_memory, i=0):
        """Set key."""
        self[i].set(key_infile, key_memory)

    def modify_key(self, key_infile=None, key_memory=None, i=0):
        """Modify key in place."""
        self[i].modify(key_infile, key_memory)

    def remove_key(self, idx):
        """Remove keys."""
        self.keys.pop(idx)

    def remove_keys(self):
        """Remove all keys."""
        self.keys = []

    def order_keys(self, order):
        """Modify keys order.

        Parameters
        ----------
        order: List of str
        """
        for k in self:
            keys_inf, keys_mem = k
            keys_inf = dict(zip(order, [keys_inf[c] for c in order]))
            keys_mem = dict(zip(order, [keys_mem[c] for c in order]))
            k.set(keys_inf, keys_mem)

    def merge_keys(self):
        """Merge successive shared keys.

        Due to the way get_commands_shared is written,
        we expect to have a series of keys for all shared
        coordinates, for the same file. All keys are list of
        integers of length one.
        The keys are varying in the order of coords_shared.

        Raises
        ------
        TypeError:
            If the one of the in-file key is not an integer.
        """
        coords = list(self[0].infile.keys())
        keys = self.keys.copy()
        for name in coords:
            coords_ = [c for c in coords if c != name]
            keys_new = []
            keys_inf_to_simplify = []
            keys_mem_to_simplify = []

            key_start = keys[0]

            for key in keys:
                merge = True
                for name_ in coords_:
                    if key[name_] != key_start[name_]:
                        merge = False

                if merge:
                    key_inf, key_mem = key[name]
                    if not isinstance(key_inf, (int, np.integer, type(None))):
                        raise TypeError("In file key must be integer or None."
                                        "(%s, %s, %s)" % (self.filename, name, key_inf))
                    assert isinstance(key_mem, (int, np.integer)), "Memory key is not integer."
                    keys_inf_to_simplify.append(key_inf)
                    keys_mem_to_simplify.append(key_mem)
                else:
                    keys_new.append(key)

            keys_inf_simplified = simplify_key(keys_inf_to_simplify)
            keys_mem_simplified = simplify_key(keys_mem_to_simplify)
            if ((not isinstance(keys_inf_simplified, slice))
                    and (not isinstance(keys_mem_simplified, slice))):
                keys_inf_simplified = keys_inf_to_simplify
                keys_mem_simplified = keys_mem_to_simplify

            key_start.modify({name: keys_inf_simplified},
                             {name: keys_mem_simplified})
            keys_new.insert(0, key_start)
            keys = keys_new.copy()

        self.remove_keys()
        self.keys = keys_new

    def join_filename(self, root):
        """Join a filename to a root directory."""
        filename = os.path.join(root, self.filename)
        self.filename = filename


def merge_cmd_per_file(commands):
    """Merge commands that correspond to the same file."""

    filenames = {cmd.filename for cmd in commands}

    commands_merged = []
    for filename in filenames:
        cmd_merged = None
        for cmd in commands:
            if cmd.filename == filename:
                if cmd_merged is None:
                    cmd_merged = cmd
                else:
                    cmd_merged += cmd

        commands_merged.append(cmd_merged)

    return commands_merged

def list2slice_simple(L):
    """Transform a list into a slice when possible.

    Step can be any integer.
    Can be descending.
    """
    if len(L) < 3:
        return L

    diff = np.diff(L)
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
