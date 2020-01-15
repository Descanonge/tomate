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

from data_loader.key import Keyring, Key


log = logging.getLogger(__name__)


class CmdKeyrings():
    """Keyrings used in a Command.

    Describe what must be taken from file and
    where it should be placed in memory.
    A key can be anything that can subset the
    data, typically a list of intereger, or a slice.

    Parameters
    ----------
    infile: Keyring
        Keys that will be taken in file.
    memory: Keyring
        Keys to indicate where to put the data
        in the memory.

    Attributes
    ----------
    infile: Keyring
        Keys that will be taken in file
    memory: Keyring
        Keys to indicate where to put the data
        in the memory.
    """

    def __init__(self, infile=None, memory=None):
        if infile is None:
            infile = Keyring()
        if memory is None:
            memory = Keyring()
        self.set(infile, memory)

    def __str__(self):
        return 'in-file: ' + str(self.infile) + ' | memory: ' + str(self.memory)

    def __iter__(self):
        return iter([self.infile, self.memory])

    def __getitem__(self, item):
        return [self.infile[item], self.memory[item]]

    def set(self, infile, memory):
        """Set keys.

        Parameters
        ----------
        infile: Keyring
        memory: Keyring
        """
        self.infile = infile
        self.memory = memory

    def modify(self, infile=None, memory=None):
        """Modify keys in place.

        Parameters
        ----------
        infile: Keyring, optional
        memory: Keyring, optional
        """
        if infile is not None:
            self.infile.update(infile)
        if memory is not None:
            self.memory.update(memory)


class Command():
    """Information for loading slices of data from one file.

    A command is composed of a filename, and
    a series of keys that each specifies a
    part of the data to take, and where to
    place it.

    Attributes
    ----------
    filename: str
        File to open
    var_list: List[str]
        Variables to take in that file.
    keyrings: List[CmdKeyrings]
        List of Keys objects to take in that file.
    """

    def __init__(self):
        self.filename = ""
        self.var_list = []
        self.keyrings = []

    def __iter__(self):
        """Iter on keys."""
        return iter(self.keyrings)

    def __str__(self):
        s = []
        s.append("file: %s" % self.filename)
        if self.var_list:
            s.append("variables: " + str(self.var_list))
        s.append("keyrings: %s" % '\n      '.join([str(k) for k in self]))
        return "\n".join(s)

    def __len__(self):
        return len(self.keyrings)

    def __getitem__(self, i):
        return self.keyrings[i]

    def __iadd__(self, other):
        """Merge two commands.

        Add the keys of one into the other.
        """
        for k in other:
            self.append(*k)
        return self

    def append(self, krg_infile, krg_memory):
        """Add a command keyring set."""
        self.keyrings.append(CmdKeyrings(krg_infile, krg_memory))

    def add_keyrings(self, krgs_infile, krgs_memory):
        """Add multiple keyrings."""
        n = len(krgs_infile)
        for i in range(n):
            self.append(krgs_infile[i], krgs_memory[i])

    def set_keyring(self, krg_infile, krg_memory, i=0):
        """Set a key by index."""
        self[i].set(krg_infile, krg_memory)

    def modify_keyring(self, krg_infile=None, krg_memory=None, i=0):
        """Modify key in place."""
        self[i].modify(krg_infile, krg_memory)

    def remove_keyring(self, idx):
        """Remove a key."""
        self.keyrings.pop(idx)

    def remove_keyrings(self):
        """Remove all keys."""
        self.keyrings = []

    def order_keys(self, order):
        """Modify all keys order.

        Parameters
        ----------
        order: List[str]
        """
        for krg in self:
            krg_inf, krg_mem = krg
            krg_inf.sort_by(order)
            krg_mem.sort_by(order)
            krg.set(krg_inf, krg_mem)

    def merge_keys(self):
        # TODO: test for multiple shared keys
        """Merge successive shared keys.

        Due to the way get_commands_shared is written,
        we expect to have a series of keyrings for all shared
        coordinates, for the same file. All keys are list of
        integers of length one.
        The keys are varying in the order of coords_shared.

        Raises
        ------
        TypeError:
            If the one of the in-file key is not an integer.
        """
        coords = list(self[0].infile.coords)
        cks = self.keyrings
        for name in coords:
            coords_ = [c for c in coords if c != name]
            # New command keyrings
            cks_new = []
            # command keyrings to simplify
            keys_inf_to_simplify = []
            keys_mem_to_simplify = []

            # First command keyrings
            ck_start = self[0]

            for ck in cks:
                merge = True
                # Check keys for other coords are identical
                for name_ in coords_:
                    if ck[name_] != ck_start[name_]:
                        merge = False

                if merge:
                    key_inf, key_mem = ck[name]
                    if key_inf.type == 'list' and len(key_inf.value) == 1:
                        key_value = key_inf.value[0]
                    else:
                        key_value = key_inf.value
                    assert key_mem.type == 'int', "Memory key is not integer."

                    keys_inf_to_simplify.append(key_value)
                    keys_mem_to_simplify.append(key_mem.value)
                else:
                    cks_new.append(ck)

            key_inf_simplified = simplify_keys(keys_inf_to_simplify)
            key_mem_simplified = simplify_keys(keys_mem_to_simplify)

            ck_start.modify({name: key_inf_simplified},
                            {name: key_mem_simplified})
            cks_new.insert(0, ck_start)
            cks = cks_new

        self.remove_keyrings()
        self.keyrings = cks_new

    def join_filename(self, root):
        """Join a filename to a root directory."""
        filename = os.path.join(root, self.filename)
        self.filename = filename


def merge_cmd_per_file(commands):
    """Merge commands that correspond to the same file.

    Parameters
    ----------
    Commands: List[Command]
    """
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


def simplify_keys(keys):
    """Simplify a list of keys.

    If possible return a slice.
    If all identical, return a single value.
    Else return a list.

    Parameters
    ----------
    keys: List[int, None, or slice]
    """
    start = keys[0]

    if all(k == start for k in keys):
        return start

    if all(isinstance(k, Key.int_types) for k in keys):
        key = Key(keys)
        key.simplify()
        return key.value

    raise TypeError("Different types of keys not mergeable.")
