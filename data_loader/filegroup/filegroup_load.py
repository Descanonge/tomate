"""Filegroup class with data loading functionnalities.

This class is abstract and is meant to be subclassed to be usable.
A subclass would replace existing functions specific to a file format.
"""

import os
import itertools
from typing import List

import numpy as np

from data_loader.filegroup.filegroup_scan import FilegroupScan


class FilegroupLoad(FilegroupScan):
    """Filegroup class with data loading functionnalies."""

    def get_commands(self, var_list, keys):
        """Retrieve filenames.

        Recreate filenames from matches.

        Parameters
        ----------
        var_list: List[str]
            List of variables names
        keys: Dict[str, NpIdx]
            Dict of coord keys to load from the data
            available
            Keys are passed to numpy arrays

        Returns
        -------
        filename: str
            Filename to load
        var_list: List[str]
        keys: Dict[str, NpIdx]
            Keys for the whole data
        keys_in: Dict[str, NpIdx]
            Keys to load in the filename
        keys_slice: Dict[str, NpIdx]
            Keys of the slice that is going to be loaded, for
            that filename, and in order.
        """
        commands = self._get_commands_inout(keys)
        commands_new = []
        for cmd in commands:
            # Add variables to load in the command
            cmd.insert(1, var_list)
            # Add keys_in for in coordinates
            self._get_command_in(cmd, keys)
            cmd = self._preprocess_load_command(*cmd)
            commands_new.append(cmd)

        return commands_new

    def _get_commands_inout(self, keys):
        """Return the combo filename / keys_in for inout coordinates."""
        # Find matches and their regex indices for reconstructing filenames,
        # And in-file indexes
        matches = []
        rgx_idxs = []
        in_idxs = []
        for name, cs in self.enum("*out").items():
            key = keys[name]
            match = []
            rgx_idx_matches = []
            for i, rgx in enumerate(cs.matchers):
                match.append(cs.matches[key, i])
                rgx_idx_matches.append(rgx.idx)

            # Matches are stored by regex index, we
            # need to transpose to have a list by filename
            match = np.array(match)
            matches.append(match.T)
            in_idxs.append(cs.in_idx[key])
            rgx_idxs.append(rgx_idx_matches)

        # Number of matches by out coordinate for looping
        lengths = []
        for i_c, _ in enumerate(matches):
            lengths.append(len(matches[i_c]))

        commands = []
        # Imbricked for loops for all out coords
        for m in itertools.product(*(range(z) for z in lengths)):
            # Reconstruct filename
            seg = self.segments.copy()
            for i_c, cs in enumerate(self.enum("*out").keys()):
                idx_rgx_matches = rgx_idxs[i_c]
                for i, rgx_idx in enumerate(idx_rgx_matches):
                    seg[2*rgx_idx+1] = matches[i_c][m[i_c]][i]
            filename = "".join(seg)

            # Find keys
            keys_slice = {}
            keys_in = {}
            i_c = 0
            for name, cs in self.enum("*out").items():
                keys_slice[name] = m[i_c]
                keys_in[name] = in_idxs[i_c][m[i_c]]
                i_c += 1

            commands.append([filename, keys_in, keys_slice])

        return commands

    def _get_command_in(self, cmd, keys):
        """Add in coords keys to the commands."""
        keys_in = {}
        keys_slice = {}
        for name, cs in self.enum("in").items():
            key = keys[name]
            keys_in[name] = cs.get_slice(key)
            # TODO: slice(None, None, -1) if reversed ?
            keys_slice[name] = slice(None, None)

        cmd[2].update(keys_in)
        cmd[3].update(keys_slice)

    def load_data(self, var_list, keys):
        """Load data."""
        commands = self.get_commands(var_list, keys)
        for cmd in commands:
            self._load_cmd(*cmd)

    def _load_cmd(self, filename, var_list, keys_in, keys_slice):
        """Load data from one file using a command.

        Parameters
        ----------
        filename: str
            Filename to open
        var_list: List[str]
            Variables to load
        keys: Dict[coord name, key]
            Keys to load in file
        """
        raise NotImplementedError

    def _get_order(self, *args) -> List[str]:
        """Get order of dimensions in file.

        Returns
        -------
        order: List[str]
            Coordinate names, in the order of the file.
        """
        raise NotImplementedError

    def _preprocess_load_command(self, filename, var_list, keys_in, keys_slice):
        """Preprocess the load command.

        Join root and filename
        Replace int keys with list, as keys is then typically
        passed to a numpy array, we will thus retain the right
        number of dimensions.

        Parameters
        ----------
        filename: str
            Filename to open
        var_list: List[str]
            Variables to load
        keys: Dict[coord name, key]
            Keys to load in file

        Returns
        -------
        cmd: [filename: str, var_list: List[str], keys]
            Command passed to self._load_cmd
        """
        filename = os.path.join(self.root, filename)

        for coord, key in keys_in.items():
            if isinstance(key, np.integer):
                keys_in[coord] = [key]

        keys_in = self.db.get_coords_kwargs(**keys_in)
        keys_in = self.db.sort_by_coords(keys_in)
        keys_slice = self.db.get_coords_kwargs(**keys_slice)
        keys_slice = self.db.sort_by_coords(keys_slice)
        return filename, var_list, keys_in, keys_slice
