"""Filegroup class with data loading functionnalities."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


import itertools
import logging
from typing import List

import numpy as np

from data_loader.filegroup.filegroup_scan import FilegroupScan
from data_loader.filegroup import command
from data_loader.key import Keyring
from data_loader.accessor import Accessor


log = logging.getLogger(__name__)


class FilegroupLoad(FilegroupScan):
    """Filegroup class with data loading functionnalies.

    This class is abstract and is meant to be subclassed to be usable.
    A subclass would replace existing functions specific to a file format.

    See :doc:`../expanding` for more information about subclassing this.
    """

    acs = Accessor

    def get_commands(self, keyring):
        """Get load commands.

        Recreate filenames from matches and find shared coords keys.
        Merge commands that have the same filename.
        If possible, merge contiguous shared keys.
        Add the keys for in coords.
        Order keys according to the database coordinate order.

        Parameters
        ----------
        var_list: List[str]
            List of variables names.
        keyring: Keyring
            Part of available data to load.

        Returns
        -------
        commands: List[Command]
        """
        commands = self._get_commands_shared(keyring)
        commands = command.merge_cmd_per_file(commands)

        # When there is no shared coordinate.
        if len(commands) == 0:
            commands = self._get_commands_no_shared()

        key_in_inf = self._get_key_infile(keyring)
        key_in_mem = self._get_key_memory(key_in_inf)

        for cmd in commands:
            cmd.join_filename(self.root)

            cmd.merge_keys()
            for key in cmd:
                key.modify(key_in_inf, key_in_mem)

            for krg_inf, krg_mem in cmd:
                krg_inf.make_list_int()
                krg_mem.make_list_int()

            cmd.order_keys(['var'] + self.db.coords_name)

        return commands

    def _get_commands_no_shared(self):
        """Get commands when there are no shared coords.

        Returns
        -------
        List[Command]
            Single command.
        """
        cmd = command.Command()
        cmd.filename = ''.join(self.segments)
        return [cmd]

    def _get_commands_shared(self, keyring):
        """Return the combo filename / keys_in for shared coordinates.

        Parameters
        ----------
        keyring: Keyring
            Part of the available data to load.

        Returns
        -------
        List[Command]
            List of command, one per combination of shared
            coordinate key.
        """
        matches, rgx_idxs, in_idxs = self._get_commands_shared__get_info(keyring)

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
            krgs_inf = Keyring()
            krgs_mem = Keyring()
            for i_c, name in enumerate(self.iter_shared(True)):
                krgs_inf[name] = in_idxs[i_c][m[i_c]]
                krgs_mem[name] = m[i_c]

            cmd.append(krgs_inf, krgs_mem)
            commands.append(cmd)

        return commands

    def _get_commands_shared__get_info(self, keyring):
        """For all asked values, retrieve matchers, regex index and in file index.

        Find matches and their regex indices for reconstructing filenames.
        Find the in-file indices as the same time.

        Parameters
        ----------
        keyring: Keyring
            Part of available data to load.

        Returns
        -------
        matches: List[Array[str]]
            Matches for all coordinates for each needed file.
            Length is the # of shared coord, each array is (# of values, # of matches per value).
        rgx_idxs: List[List[int]]
            Corresponding indices of matches in the regex.
        in_idxs: List[int], None
            In file indices of asked values.
        """
        matches = []
        rgx_idxs = []
        in_idxs = []
        for name, cs in self.iter_shared(True).items():
            key = keyring[name].no_int()
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

    def _get_key_infile(self, keyring):
        """Get the keys for data in file.

        Parameters
        ----------
        keyring: Keyring
        """
        krg_inf = Keyring()
        for name, cs in self.iter_shared(False).items():
            key_inf = cs.get_in_idx(keyring[name])
            krg_inf[name] = key_inf
        krg_inf.simplify()
        return krg_inf

    def _get_key_memory(self, keyring):
        """Get the keys for data in memory.

        Parameter
        ---------
        keyring: Keyring
            Keyring asked to the filegroup.
        """
        krg_mem = Keyring()
        for name in self.iter_shared(False):
            key = keyring[name]
            if key.type == 'int':
                key_mem = 0
            elif key.type == 'list':
                key_mem = list(range(0, self.db.loaded[name].size, 1))
            elif key.type in ['slice', 'none']:
                key_mem = slice(0, self.db.loaded[name].size, 1)
            krg_mem[name] = key_mem
        return krg_mem

    def load_data(self, keyring):
        """Load data for that filegroup.

        Retrieve load commands.
        Open file, load data, close file.

        Parameters
        ----------
        var_list: List[str]
            Variables to load
        keyring: Keyring
        """
        commands = self.get_commands(keyring)
        for cmd in commands:
            log.debug('Command: %s', str(cmd).replace('\n', '\n\t'))
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

        See :doc:`../filegroup` and :doc:`../expanding`
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

    def _get_order(self, file):
        """Get order of dimensions in file.

        Parameters
        ----------
        file: File object

        Returns
        -------
        order: List[str]
            Dimensions names, in the order of the file.
        """
        raise NotImplementedError

    @staticmethod
    def _get_internal_keyring(order, keyring) -> Keyring:
        """Get keyring for in file taking.

        If dimension that are not known by the filegroup,
        and thus not in the keyring, take the first index.

        Remove any keys from dimension not in the file.

        Put the keyring in order.
        """
        int_krg = keyring.copy()
        for dim in order:
            if dim not in int_krg:
                int_krg[dim] = 0
        return int_krg.subset(order)
    
    def reorder_chunk(self, chunk, coords, order=None, variables=False):
        """Reorder data.

        Dimensions are not necessarily stored with the same
        order in file and in memory.

        Parameters
        ----------
        chunk: Numpy array
            Data chunk taken from file and to re-order.
        coords: List[str]
            Dimensions asked for loading.
        order: List[str], optional
            Dimensions names ordered as in file.
        variables: bool, optional
            If there is a variable dimension in the data
            chunk. If there is, it should be the first one
            (ie on the axis #0).

        Returns
        -------
        Array
            Re-ordered data.
        """
        if order is None:
            order = list(self.cs.keys())

        coords = [c for c in coords if c in order]

        # Reorder array
        if variables:
            order.insert(0, 'var')
            coords.insert(0, 'var')
        source = [coords.index(n) for n in coords if n in order]
        dest = [coords.index(n) for n in order]

        if source != dest:
            log.info("reordering %s -> %s", source, dest)
            chunk = self.acs.moveaxis(chunk, source, dest)

        return chunk

    def write_add_variable(self, var, sibling, inf_name, scope):
        keyring = scope.parent_keyring.copy()
        keyring['var'] = sibling
        keyring.make_var_idx(self.contains)

        commands = self.get_commands(keyring)

        for cmd in commands:
            log.debug('Command: %s', str(cmd).replace('\n', '\n\t'))
            file = self.open_file(cmd.filename, mode='r+', log_lvl='info')
            for cks in cmd:
                cks.memory['var'] = self.db.idx(var)
            try:
                self.write_variable(file, cmd, var, inf_name)
            except:
                self.close_file(file)
                raise
            else:
                self.close_file(file)
