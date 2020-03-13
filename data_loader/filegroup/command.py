"""For specifying how to load data."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


import os
import logging
from typing import Iterator

from data_loader.key import Keyring, Key


log = logging.getLogger(__name__)


class CmdKeyrings():
    """Keyrings used in a Command.

    Describe what must be taken from file and
    where it should be placed in memory.

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
        """Returns both keyrings.

        Yields
        ------
        Iterator[Keyring]
            Infile and memory keyrings.
        """
        return iter([self.infile, self.memory])

    def __getitem__(self, item):
        """Get keys from both keyrings.

        Returns
        -------
        List[Key]
            Key for `item` dimension in
            infile and memory keyrings.
        """
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

    def copy(self):
        infile = self.infile.copy()
        memory = self.memory.copy()
        return CmdKeyrings(infile, memory)


class Command():
    """Information for loading slices of data from one file.

    A command is composed of a filename, and
    a series of keyrings duos that each specifies a
    part of the data to take, and where to
    place it.

    Attributes
    ----------
    filename: str
        File to open.
    var_list: List[str]
        Variables to take in that file.
    keyrings: List[CmdKeyrings]
        List of keyrings that tell what to take in the file,
        and where to place it.
    """

    def __init__(self):
        self.filename = ""
        self.keyrings = []

    def __iter__(self) -> Iterator[CmdKeyrings]:
        """Iter on keyrings duos."""
        return iter(self.keyrings)

    def __str__(self):
        s = []
        s.append("file: %s" % self.filename)
        s.append("keyrings: %s" % '\n      '.join([str(k) for k in self]))
        return "\n".join(s)

    def __len__(self) -> int:
        """Number of keyrings duos."""
        return len(self.keyrings)

    def __getitem__(self, i) -> CmdKeyrings:
        """Get i-th keyrings duo."""
        return self.keyrings[i]

    def __iadd__(self, other: "Command") -> "Command":
        """Merge two commands.

        Add the keys of one into the other.
        """
        for k in other:
            self.append(*k)
        return self

    def append(self, krg_infile, krg_memory):
        """Add a command keyring duo.

        Parameters
        ----------
        krg_infile, krg_memory: Keyring
        """
        self.keyrings.append(CmdKeyrings(krg_infile, krg_memory))

    def add_keyrings(self, krgs_infile, krgs_memory):
        """Add multiple keyrings duos.

        Parameters
        ----------
        krgs_infile, krgs_memory: List[Keyring]
        """
        n = len(krgs_infile)
        for i in range(n):
            self.append(krgs_infile[i], krgs_memory[i])

    def set_keyring(self, krg_infile, krg_memory, i=0):
        """Set a keyrings duo by index.

        Parameters
        ----------
        krg_infile, krg_memory: Keyring
        i: int, optional
            Index.
        """
        self[i].set(krg_infile, krg_memory)

    def modify_keyring(self, krg_infile=None, krg_memory=None, i=0):
        """Modify a keyrings duo in place.

        Parameters
        ----------
        krg_infile, krg_memory: Keyring, optional
        i: int, optional
             Index.
        """
        self[i].modify(krg_infile, krg_memory)

    def remove_keyring(self, idx: int):
        """Remove a key."""
        self.keyrings.pop(idx)

    def remove_keyrings(self):
        """Remove all keys."""
        self.keyrings = []

    def copy(self):
        new = Command()
        new.filename = self.filename

        for krg in self:
            krg_ = krg.copy()
            new.append(*krg_)
        return new

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
        coords = list(self[0].infile.dims)
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

    def join_filename(self, root: str):
        """Join a filename to a root directory."""
        filename = os.path.join(root, self.filename)
        self.filename = filename


def merge_cmd_per_file(commands):
    """Merge commands that correspond to the same file.

    Parameters
    ----------
    Commands: List[Command]
    """
    filenames = []
    for cmd in commands:
        if cmd.filename not in filenames:
            filenames.append(cmd.filename)

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


def separate_variables(commands):
    """.

    Does not support slices (yet).
    """
    commands_ = []
    for cmd in commands:
        print(cmd)
        cmd_ = cmd.copy()
        cmd_.remove_keyrings()
        for krg in cmd:
            for inf, mem in zip(krg.infile['var'].iter(), krg.memory['var'].iter()):
                krg_ = krg.copy()
                krg_.infile['var'].value = inf[0]
                krg_.infile['var'].name = inf[1]
                krg_.infile['var'].type = 'int'
                krg_.infile['var'].shape = 0
                krg_.memory['var'].value = mem[0]
                krg_.memory['var'].name = mem[1]
                krg_.memory['var'].type = 'int'
                krg_.memory['var'].shape = 0
                cmd_.append(*krg_)
        commands_.append(cmd_)
    return commands_
