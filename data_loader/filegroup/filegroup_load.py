"""Filegroup class with data loading functionnalities."""

import itertools
import logging

import numpy as np

from data_loader.filegroup.filegroup_scan import FilegroupScan
from data_loader.filegroup import command

log = logging.getLogger(__name__)


class FilegroupLoad(FilegroupScan):
    """Filegroup class with data loading functionnalies.

    This class is abstract and is meant to be subclassed to be usable.
    A subclass would replace existing functions specific to a file format.
    """

    def get_commands(self, var_list, keys):
        """Get load commands.

        Recreate filenames from matches and find shared coords keys.
        Merge commands that have the same filename.
        If possible, merge contiguous shared keys.
        Add the keys for in coords.
        Order keys according to the database coordinate order.

        Parameters
        ----------
        var_list: List[str]
            List of variables names
        keys: Dict[coordinate: str, key: slice or List[int]
            Part of coordinates to load from the data
            available.

        Returns
        -------
        commands: List[Command]
        """
        commands = self._get_commands_shared(keys)
        commands = command.merge_cmd_per_file(commands)

        if len(commands) == 0:
            commands = self._get_commands_no_shared()

        key_inf = self._get_key_infile(keys)
        key_mem = self._get_key_memory(keys)

        for cmd in commands:
            cmd.join_filename(self.root)
            cmd.var_list = var_list

            cmd.merge_keys()

            for key in cmd:
                key.modify(key_inf, key_mem)

            cmd.order_keys(self.db.coords_name)

        return commands

    def _get_commands_no_shared(self):
        """Get commands when there are no shared coords."""
        cmd = command.Command()
        cmd.filename = ''.join(self.segments)
        return [cmd]

    def _get_commands_shared(self, keys):
        """Return the combo filename / keys_in for shared coordinates."""
        matches, rgx_idxs, in_idxs = self._get_commands_shared__get_info(keys)

        # Number of matches ordered by shared coordinates
        lengths = [len(m_c) for m_c in matches]

        commands = []
        seg = self.segments.copy()
        # Imbricked for loops (one per shared coord)
        for m in itertools.product(*(range(z) for z in lengths)):
            cmd = command.Command()

            # Reconstruct filename
            for i_c, _ in enumerate(self.iter_shared(True).keys()):
                for i, rgx_idx in enumerate(rgx_idxs[i_c]):
                    seg[2*rgx_idx+1] = matches[i_c][m[i_c]][i]
            cmd.filename = "".join(seg)

            # Find keys
            keys_mem = {}
            keys_inf = {}
            for i_c, name in enumerate(self.iter_shared(True)):
                keys_mem[name] = m[i_c]
                keys_inf[name] = in_idxs[i_c][m[i_c]]

            cmd.append(keys_inf, keys_mem)
            commands.append(cmd)

        return commands

    def _get_commands_shared__get_info(self, keys):
        """For all asked values, retrieve matchers, regex index and in file index.

        Find matches and their regex indices for reconstructing filenames.
        Find the in-file indices as the same time.

        Parameters
        ----------
        keys: Dict[keys]
            Dict of askey coordinates slices.

        Returns
        -------
        matches: List of matches for each coord.
            Matches for all coordinates for each needed file.
            Length is the # of shared coord, each array is (# of values, # of matches per value).
        rgx_idxs: List[ List[int] ]
            Corresponding indices of matches in the regex.
        in_idxs: List[int] or None
            In file indices of asked values.
        """
        matches = []
        rgx_idxs = []
        in_idxs = []
        for name, cs in self.iter_shared(True).items():
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

        return matches, rgx_idxs, in_idxs

    def _get_key_infile(self, keys):
        """Get the keys for data in file."""
        keys_inf = {}
        for name, cs in self.iter_shared(False).items():
            key = keys[name]
            key_inf = cs.get_in_idx(key)
            key_inf = command.simplify_key(key_inf)
            keys_inf[name] = key_inf
        return keys_inf

    def _get_key_memory(self, keys):
        """Get the keys for data in memory."""
        keys_mem = {}
        for name in self.iter_shared(False):
            key_mem = list(range(self.db[name].size))
            key_mem = command.simplify_key(key_mem)
            keys_mem[name] = key_mem
        return keys_mem

    def load_data(self, var_list, keys):
        """Load data for that filegroup.

        Retrieve load commands.
        Open file, load data, close file.

        Parameters
        ----------
        var_list: List[str]
            Variables to load
        keys: Dict[coordinate: str, key: slice or List[int]]
        """
        commands = self.get_commands(var_list, keys)
        for cmd in commands:
            log.debug(cmd)
            file = self.open_file(cmd.filename, mode='r', log_lvl='info')
            try:
                self.load_cmd(file, cmd)
            except:
                self.close_file(file)
                raise
            else:
                self.close_file(file)

    def load_cmd(self, file, cmd):
        """Load data from one file using a load command.

        Load content following a 'load command'.
        See documentation on filegroups and expanding the package
        for more information on how this function works, and
        how to implement it.

        Parameters
        ----------
        file:
            Object to access file.
            The file is already opened by FilegroupScan.open_file().
        cmd: Command
            Load command.
        """
        raise NotImplementedError

    def _get_order(self, *args):
        """Get order of dimensions in file.

        Returns
        -------
        order: List[str]
            Coordinate names, in the order of the file.
        """
        raise NotImplementedError

    def reorder_chunk(self, chunk, keys, order=None):
        """Reorder data.

        Dimensions are not necessarily stored with the same
        order in file and in memory.

        Parameters
        ----------
        order: List[str]
            Coordinates names ordered as in file.
        keys: List[str]
            Coordinates keys asked for loading.
        chunk: Numpy array
            Data chunk taken from file and to re-order.
        variables: bool, optional
            If there is a variable dimension in the data
            chunk. If there is, it should be the first one
            (ie on the axis #0).

        Returns
        -------
        chunk:
            Data array.
        """
        if order is None:
            order = list(self.cs.keys())

        # If we ask for keys that are not in the file.
        # added dimensions are inserted at the begginning
        order_added = order.copy()
        for k in keys:
            if k not in order:
                chunk = chunk.reshape((1, *chunk.shape))
                order_added.insert(0, k)

        # Reorder array
        target = [self.db.coords_name.index(z) for z in order_added]
        current = list(range(len(target)))
        if target != current:
            log.info("reordering %s -> %s", current, target)
            chunk = np.moveaxis(chunk, current, target)

        return chunk
