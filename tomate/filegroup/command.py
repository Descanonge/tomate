"""For specifying how to load data."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import os
import logging
from typing import Iterator, List, Tuple

from tomate.keys.key import Key
from tomate.keys.keyring import Keyring


log = logging.getLogger(__name__)


class CmdKeyrings():
    """Keyrings used in a Command.

    Describe what must be taken from file and
    where it should be placed in memory.

    :param infile: Keys that will be taken in file.
    :param memory: Keys to indicate where to put the data
        in the memory.

    :attr infile: Keyring: Keys that will be taken in file
    :attr memory: Keyring: Keys to indicate where to put the data
        in the memory.
    """

    def __init__(self, infile: Keyring = None, memory: Keyring = None):
        if infile is None:
            infile = Keyring()
        if memory is None:
            memory = Keyring()
        self.set(infile, memory)

    def __repr__(self):
        s = 'in-file: {} | memory: {}'.format(str(self.infile),
                                              str(self.memory))
        return s

    def __iter__(self) -> Iterator[Keyring]:
        """Returns both infile and memory keyrings."""
        return iter([self.infile, self.memory])

    def __getitem__(self, item: str) -> Tuple[Keyring, Keyring]:
        """Get keys from both keyrings for a dimension."""
        return (self.infile[item], self.memory[item])

    def set(self, infile: Keyring, memory: Keyring):
        """Set keys."""
        self.infile = infile
        self.memory = memory

    def modify(self, infile: Keyring = None, memory: Keyring = None):
        """Modify keys in place.

        :param infile: [opt]
        :param memory: [opt]
        """
        if infile is not None:
            self.infile.update(infile)
        if memory is not None:
            self.memory.update(memory)

    def copy(self) -> "CmdKeyrings":
        """Return copy of self."""
        infile = self.infile.copy()
        memory = self.memory.copy()
        return CmdKeyrings(infile, memory)


class Command():
    """Information for loading slices of data from one file.

    A command is composed of a filename, and
    a series of keyrings duos that each specifies a
    part of the data to take, and where to
    place it.

    :attr filename: str: File to open.
    :attr var_list: List[str]: Variables to take in that file.
    :attr keyrings: List[CmdKeyrings]: List of keyrings that tell
        what to take in the file, and where to place it.
    """

    def __init__(self):
        self.filename = ""
        self.keyrings = []

    def __iter__(self) -> Iterator[CmdKeyrings]:
        """Iter on keyrings duos."""
        return iter(self.keyrings)

    def __repr__(self):
        s = []
        s.append(f"file: {self.filename}")
        s.append("keyrings: {}".format('\n      '.join([str(k) for k in self])))
        return "\n".join(s)

    def __len__(self) -> int:
        """Number of keyrings duos."""
        return len(self.keyrings)

    def __getitem__(self, i: int) -> CmdKeyrings:
        """Get i-th keyrings duo."""
        return self.keyrings[i]

    def __iadd__(self, other: "Command") -> "Command":
        """Merge two commands.

        Add the keys of one into the other.
        """
        for k in other:
            self.append(*k)
        return self

    def append(self, krg_infile: Keyring, krg_memory: Keyring):
        """Add a command keyring duo."""
        self.keyrings.append(CmdKeyrings(krg_infile, krg_memory))

    def add_keyrings(self, krgs_infile: List[Keyring], krgs_memory: List[Keyring]):
        """Add multiple keyrings duos."""
        n = len(krgs_infile)
        for i in range(n):
            self.append(krgs_infile[i], krgs_memory[i])

    def set_keyring(self, krg_infile: Keyring, krg_memory: Keyring, i=0):
        """Set a keyrings duo by index."""
        self[i].set(krg_infile, krg_memory)

    def modify_keyring(self, krg_infile: Keyring = None, krg_memory: Keyring = None,
                       i: int = 0):
        """Modify a keyrings duo in place."""
        self[i].modify(krg_infile, krg_memory)

    def remove_keyring(self, idx: int):
        """Remove a key."""
        self.keyrings.pop(idx)

    def remove_keyrings(self):
        """Remove all keys."""
        self.keyrings = []

    def copy(self) -> "Command":
        """Return copy of self."""
        new = Command()
        new.filename = self.filename

        for krg in self:
            krg_ = krg.copy()
            new.append(*krg_)
        return new

    def order_keys(self, order: List[str]):
        """Modify all keys order."""
        for krg in self:
            krg_inf, krg_mem = krg
            krg_inf.sort_by(order)
            krg_mem.sort_by(order)
            krg.set(krg_inf, krg_mem)

    def merge_keys(self):
        """Merge successive shared keys.

        Due to the way get_commands_shared is written,
        we expect to have a series of keyrings for all shared
        coordinates, for the same file. All keys are list of
        integers of length one.
        The keys are varying in the order of coords_shared.

        :raises TypeError: If the one of the in-file key is not an integer.
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
            ck_start = cks[0]

            for ck in cks:
                merge = True
                # Check keys for other coords are identical
                for name_ in coords_:
                    if ck[name_] != ck_start[name_]:
                        merge = False

                if merge:
                    key_inf, key_mem = ck[name]
                    key_inf.make_list_int()
                    key_mem.make_list_int()
                    keys_inf_to_simplify.append(key_inf)
                    keys_mem_to_simplify.append(key_mem)
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


def merge_cmd_per_file(commands: List[Command]) -> List[Command]:
    """Merge commands that correspond to the same file."""
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


def simplify_keys(keys: List[Key]) -> Key:
    """Simplify a list of keys.

    If possible return a slice.
    If all identical, return an integer key.
    Else return a list key.

    :raises ValueError: If keys are not all identical, or
        of not of type int.
    """
    start = keys[0]
    if all(k == start for k in keys):
        return start

    if all(k.type == 'int' for k in keys):
        key = start.__class__([k.value for k in keys])
        key.simplify()
        key.shape = len(keys)
        return key

    raise ValueError("Keys not mergeable.")


def separate_variables(commands: List[Command]) -> List[Command]:
    """Separate commands with different variables.

    Make copies of commands.
    """
    commands_ = []
    for cmd in commands:
        cmd_ = cmd.copy()
        cmd_.remove_keyrings()
        for krg in cmd:
            for inf, mem in zip(krg.infile['var'], krg.memory['var']):
                krg_ = krg.copy()
                krg_.infile['var'].set(inf)
                krg_.memory['var'].set(mem)
                cmd_.append(*krg_)
        commands_.append(cmd_)
    return commands_
