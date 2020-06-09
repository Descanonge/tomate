"""Filegroup class with data loading functionnalities."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import itertools
import logging
from typing import Callable, Dict, List, Tuple, Union, TYPE_CHECKING

import numpy as np

from tomate.accessor import Accessor
from tomate.custom_types import File
from tomate.coordinates.variables import Variables
from tomate.filegroup import command
from tomate.filegroup.command import CmdKeyrings, Command
from tomate.filegroup.filegroup_scan import FilegroupScan
from tomate.keys.key import KeyVar
from tomate.keys.keyring import Keyring
from tomate.scope import Scope

if TYPE_CHECKING:
    from tomate.data_base import DataBase

log = logging.getLogger(__name__)


class FilegroupLoad(FilegroupScan):
    """Filegroup class with data loading functionnalies.

    This class is abstract and is meant to be subclassed to be usable.
    A subclass would replace functions specific to a file format.

    See :doc:`../expanding` for more information about subclassing this.
    """

    acs = Accessor  #: Accessor type used to fetch data in files.

    def load_from_available(self, keyring: Keyring) -> bool:
        """Load data.

        :param keyring: Data to load. Acting on available scope.

        :returns: False if nothing was loaded, True otherwise.
        """
        cmd = self.get_fg_keyrings(keyring)
        if cmd is None:
            return False
        self.load(*cmd)

        return True

    def load(self, keyring: Keyring, memory: Keyring):
        """Load data for that filegroup.

        Retrieve load commands.
        Open file, load data, close file.

        :param keyring: Data to load. Acting on this filegroup CS.
        :param memory: Corresponding memory keyring.
        """
        commands = self.get_commands(keyring, memory)
        for cmd in commands:
            log.debug('Command: %s', str(cmd).replace('\n', '\n\t'))
            file = self.open_file(cmd.filename, mode='r', log_lvl='info')
            try:
                self.load_cmd(file, cmd)
            except Exception:
                self.close_file(file)
                raise
            else:
                self.close_file(file)

        self.do_post_loading(keyring)

    def get_fg_keyrings(self, keyring: Keyring) -> CmdKeyrings:
        """Get filegroup specific keyring.

        Use `contains` attribute to translate
        keyring acting on available scope to acting
        on the filegroup alone.

        :param keyring: Keyring acting on database avail.

        :returns: Infile and memory keyrings for this filegroup.
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

        return CmdKeyrings(krg_infile, krg_memory)

    def get_commands(self, keyring: Keyring, memory: Keyring) -> List[Command]:
        """Get load commands.

        Recreate filenames from matches and find in file indices..
        Merge commands that have the same filename.
        If possible, merge contiguous shared keys.
        Add the keys for in coords.
        Favor integers and slices keys.
        Order keys according to the database coordinate order.

        :param keyring: Data to load. Acting on this filegroup CS.
        :param memory: Corresponding memory keyring.
        """
        if len(self.iter_shared(True)) == 0:
            commands = self._get_commands_no_shared()
        else:
            commands = self._get_commands_shared(keyring, memory)
            commands = command.merge_cmd_per_file(commands)

        key_in_inf = self._get_key_infile(keyring)
        key_in_mem = memory.subset(self.iter_shared(False))

        for cmd in commands:
            cmd.join_filename(self.root)

            if len(cmd) > 0:
                cmd.merge_keys()
            else:
                cmd.append(Keyring(), Keyring())

            for key in cmd:
                key.modify(key_in_inf, key_in_mem)

            for krg_inf, krg_mem in cmd:
                krg_inf.make_list_int()
                krg_mem.make_list_int()

                if not krg_inf.is_shape_equivalent(krg_mem):
                    raise IndexError("Infile and memory keyrings have different"
                                     f" shapes ({cmd})")

            cmd.order_keys(keyring.dims)

        return commands

    def _get_commands_no_shared(self) -> List[Command]:
        """Get commands when there are no shared coords."""
        cmd = command.Command()
        cmd.filename = ''.join(self.segments)
        return [cmd]

    def _get_commands_shared(self, keyring: Keyring, memory: Keyring) -> List[Command]:
        """Return the combo filename / keys_in for shared coordinates.

        :param keyring: Data to load. Acting on this filegroup CS.
        :param memory: Corresponding memory keyring.

        :returns: List of command, one per combination of shared
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

    def _get_commands_shared__get_info(self,
                                       keyring: Keyring) -> Tuple[List[np.ndarray],
                                                                  List[List[int]],
                                                                  Union[List[int], None]]:
        """For all asked values, retrieve matchers, regex index and in file index.

        Find matches and their regex indices for reconstructing filenames.
        Find the in-file indices as the same time.

        :param keyring: Data to load. Acting on this filegroup CS.

        :returns:
            matches
                Matches for all coordinates for each needed file.
                Length is the # of shared coord, each array is
                (# of values, # of matches per value).
            rgx_idxs
                Corresponding indices of matches in the regex.
            in_idxs
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

    def _get_key_infile(self, keyring: Keyring) -> Keyring:
        """Get the keys for data in file.

        :param keyring: Data to load. Acting on this filegroup CS.
        """
        krg_inf = Keyring()
        for name, cs in self.iter_shared(False).items():
            key_inf = cs.get_in_idx(keyring[name])
            krg_inf[name] = key_inf
        krg_inf.simplify()
        return krg_inf

    def load_cmd(self, file: File, cmd: Command):
        """Load data from one file using a load command.

        Load content following a 'load command'.

        See :doc:`../filegroup` and :doc:`../expanding`
        for more information on how this function works, and
        how to implement it.

        :param file: Object to access file.
            The file is already opened by FilegroupScan.open_file().
        :param cmd: Load command.
        """
        raise NotImplementedError

    def _get_order_in_file(self) -> List[str]:
        """Get order of dimensions in file.

        Default to the order of coordinates in the filegroup.

        :returns: Dimensions names as in the file, in the order of the file.
        """
        return list(self.cs.keys())

    def _get_order(self, order_file: List[str]) -> List[str]:
        """Get order of dimensions in file with their database names.

        Keep the order, change the name of the CoordScan if
        different from the Coord.
        If the in-file dimension is not associated with any database
        coordinate, keep it as is.

        :param order_file: Dimensions order as in file.

        :returns: Dimensions order, with their database name.
        """
        rosetta = {cs.name: name for name, cs in self.cs.items()}
        order = [rosetta.get(d, d) for d in order_file]
        return order

    @staticmethod
    def _get_internal_keyring(order: List[str], keyring: Keyring) -> Keyring:
        """Get keyring for in file.

        If dimension that are not known by the filegroup,
        and thus not in the keyring, take the first index.

        Remove any keys from dimension not in the file.
        (ie when key is None).

        Put the keyring in order.

        :param order: Order of dimensions in-file, as they appear in
            the database.
        :returns: Keyring to take the data.
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
                raise KeyError(f"A None key was issued for '{dim}' dimension"
                               " which is present in file.")

        int_krg = int_krg.subset(order)
        return int_krg

    def reorder_chunk(self, chunk: np.ndarray,
                      keyring: Keyring, int_keyring: Keyring) -> np.ndarray:
        """Reorder data.

        Dimensions are not necessarily stored with the same
        order in file and in memory.

        :param chunk: Data chunk taken from file and to re-order.
        :param keyring: Keyring asked. It contains the dimensions as
            they should be stored in the database.
        :param int_keyring: Keyring used to fetch chunk array from file.
            It contains the dimensions in the order of
            array.

        :returns: Re-ordered data.
        """
        in_file = int_keyring.get_non_zeros()
        in_data = [c for c in keyring.get_non_zeros() if c in in_file]
        source = [in_data.index(n) for n in in_data if n in in_file]
        dest = [in_data.index(n) for n in in_file]

        if source != dest:
            log.info("reordering %s -> %s", source, dest)
            chunk = self.acs.moveaxis(chunk, source, dest)

        return chunk

    def do_post_loading(self, keyring: Keyring):
        """Apply post loading functions."""
        do_post_loading(keyring['var'], self.db, self.cs['var'],
                        self.post_loading_funcs)

    def scan_variables_attributes(self):
        """Scan for variables specific attributes.

        Issues load commands to find for each variable
        a file in which it lies.
        For each command, use user defined function to
        scan attributes.
        Store them in VI.
        """
        keyring = Keyring(**{dim: 0 for dim in self.cs})
        keyring['var'] = list(range(self.cs['var'].size))
        cmds = self.get_commands(keyring, keyring.copy())

        for cmd in cmds:
            for infile, memory in cmd:
                memory.make_idx_var(self.cs['var'])
                log.debug('Scanning %s for variables specific attributes.', cmd.filename)

                try:
                    file = self.open_file(cmd.filename, 'r', 'debug')
                    func, _, kwargs = self.scan_attr['var']

                    attrs = func(self, file, infile['var'].tolist(), **kwargs)

                    for name, [name_inf, values] in zip(memory['var'].tolist(), attrs.items()):
                        log.debug("Found attributes (%s) for '%s' (%s infile)",
                                  values.keys(), name, name_inf)
                        already_present = [attr for attr in values
                                           if (name, attr) in self.vi]
                        for attr in already_present:
                            values.pop(attr)
                        self.vi.set_attrs(name, **values)
                except Exception:
                    self.close_file(file)
                    raise
                else:
                    self.close_file(file)

    def write_variable(self, file, cmd, var, inf_name):
        pass

    def write_add_variable(self, var: str, sibling: str,
                           inf_name: str, scope: Scope):
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
            except Exception:
                self.close_file(file)
                raise
            else:
                self.close_file(file)


def do_post_loading(key_loaded: KeyVar,
                    database: 'DataBase', variables: Variables,
                    post_loading_funcs: List[Tuple[Callable, KeyVar, bool, Dict]]):
    """Apply post loading functions."""
    loaded = set(variables[key_loaded.no_int()])
    for func, key_var, all_var, kwargs in post_loading_funcs:
        if not key_var.var and key_var.type != 'none' and key_var.value != slice(None):
            raise TypeError("Variables must be specified by name (or by None).")
        var = set(variables[key_var.no_int()])

        if all_var:
            if var <= loaded:
                func(database, **kwargs)
        else:
            if len(var & loaded) > 0:
                func(database, **kwargs)
