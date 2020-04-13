"""Filegroup class with data loading functionnalities."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


import itertools
import logging

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

    def get_fg_keyrings(self, keyring):
        """Get filegroup specific keyring.

        Use `contains` attribute to translate
        keyring acting on available scope to acting
        on the filegroup alone.

        Parameters
        ----------
        keyring: Keyring
            Keyring acting on database avail.

        Returns
        -------
        CmdKeyrings, None
            Infile and memory keyrings for this filegroup.
            None if there is nothing to load in this filegroup.
        """
        krg_infile = Keyring()
        krg_memory = Keyring()

        for dim, key in keyring.items_values():
            infile = np.array(self.contains[dim][key])
            memory = np.arange(len(infile))

            none = np.where(np.equal(infile, None))[0]
            infile = np.delete(infile, none)
            memory = np.delete(memory, none)

            if len(infile) == 0:
                return None

            krg_infile[dim] = infile
            krg_memory[dim] = memory

        krg_infile.simplify()
        krg_memory.simplify()

        msg = "Infile and memory Fg keyrings not shape equivalent."
        assert krg_infile.is_shape_equivalent(krg_memory), msg

        return command.CmdKeyrings(krg_infile, krg_memory)

    def get_commands(self, keyring, memory):
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
        commands = self._get_commands_shared(keyring, memory)
        commands = command.merge_cmd_per_file(commands)

        # When there is no shared coordinate.
        if len(commands) == 0:
            commands = self._get_commands_no_shared()

        key_in_inf = self._get_key_infile(keyring)
        key_in_mem = memory.subset(self.iter_shared(False))

        for cmd in commands:
            cmd.join_filename(self.root)

            cmd.merge_keys()
            for key in cmd:
                key.modify(key_in_inf, key_in_mem)

            for krg_inf, krg_mem in cmd:
                krg_inf.make_list_int()
                krg_mem.make_list_int()

                if not krg_inf.is_shape_equivalent(krg_mem):
                    raise IndexError("Infile and memory keyrings have different"
                                     " shapes (%s)" % str(cmd))

            cmd.order_keys(keyring.dims)

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

    def _get_commands_shared(self, keyring, memory):
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
                krgs_mem[name] = memory[name].tolist()[m[i_c]]

            cmd.append(krgs_inf, krgs_mem)
            commands.append(cmd)

        return commands

    def _get_commands_shared__get_info(self, keyring):
        # TODO: simplify
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

    def load_data(self, keyring, memory):
        """Load data for that filegroup.

        Retrieve load commands.
        Open file, load data, close file.

        Parameters
        ----------
        var_list: List[str]
            Variables to load
        keyring: Keyring
        """
        commands = self.get_commands(keyring, memory)
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

    def _get_order_in_file(self):
        """Get order of dimensions in file.

        Default to the order of `cs` in the filegroup.

        Returns
        -------
        order: List[str]
            Dimensions names as in the file, in the order of the file.
        """
        return list(self.cs.keys())

    def _get_order(self, order_file):
        """Get order of dimensions with their database names.

        Keep the order, change the name of the CoordScan is
        different from the Coord.
        If the in-file dimension is not associated with any Coord,
        keep it as is.

        Parameters
        ----------
        order_file: List[str]
            Dimensions order as in file.
        """
        rosetta = {cs.name: name for name, cs in self.cs.items()}
        order = [rosetta.get(d, d) for d in order_file]
        return order

    @staticmethod
    def _get_internal_keyring(order, keyring) -> Keyring:
        """Get keyring for in file taking.

        If dimension that are not known by the filegroup,
        and thus not in the keyring, take the first index.

        Remove any keys from dimension not in the file.
        (ie when key is None).

        Put the keyring in order.

        Parameters
        ----------
        order: List[str]
            Order of dimensions in-file, rather their associated
            name in the database if it exists.
        keyring: Keyring
        """
        int_krg = keyring.copy()
        for dim in order:
            if dim not in keyring:
                log.warning("Additional dimension %s in file."
                            " Index 0 will be taken.", dim)
                key = 0
            else:
                key = keyring[dim]
            int_krg[dim] = key

            if int_krg[dim].type == 'none':
                int_krg.pop(dim)
        int_krg = int_krg.subset(order)
        return int_krg

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

    def scan_variables_attributes(self):
        """Scan for variables specific attributes."""
        keyring = Keyring(**{dim: 0 for dim in self.cs})
        keyring['var'] = list(range(self.cs['var'].size))
        cmds = self.get_commands(keyring, keyring.copy())

        for cmd in cmds:
            for infile, memory in cmd:
                memory.make_idx_var(self.cs['var'])
                log.debug('Scanning %s for variables specific attributes.', cmd.filename)
                file = self.open_file(cmd.filename, 'r', 'debug')
                func, _, kwargs = self.scan_attr['var']

                attrs = func(file, infile['var'].tolist(), **kwargs)

                for name, [name_inf, values] in zip(memory['var'].tolist(), attrs.items()):
                    log.debug("Found attributes (%s) for '%s' (%s infile)",
                              values.keys(), name, name_inf)
                    self.vi.add_attrs_per_variable(name, values)

    def write_add_variable(self, var, sibling, inf_name, scope):
        """Add variable to files."""
        keyring = scope.parent_keyring.copy()
        keyring['var'] = sibling
        keyring.make_var_idx(self.variables)

        # FIXME: memory keyring is wrong
        commands = self.get_commands(keyring, None)

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
