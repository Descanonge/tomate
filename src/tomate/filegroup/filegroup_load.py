"""Filegroup class with data loading functionnalities."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import os
import itertools
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from tomate.accessor import Accessor
from tomate.custom_types import File, KeyLike
from tomate.filegroup import command
from tomate.filegroup.command import CmdKeyrings, Command, separate_variables
from tomate.filegroup.filegroup_scan import FilegroupScan
from tomate.keys.keyring import Keyring


log = logging.getLogger(__name__)


class FilegroupLoad(FilegroupScan):
    """Filegroup class with data loading functionnalities.

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

        Retrieve load commands. Open file, load data, close file.

        :param keyring: Data to load, acting on this filegroup scope.
        :param memory: Corresponding memory keyring, acting on loaded scope.
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

    def get_fg_keyrings(self, keyring: Keyring) -> Optional[CmdKeyrings]:
        """Get filegroup specific keyring.

        Use `contains` attribute to translate keyring acting on available scope
        to acting on the filegroup alone.

        :param keyring: Keyring acting on database available scope.
        :returns: Infile and memory keyrings for this filegroup.
            None if there is nothing to load in this filegroup.
        """
        krg_infile = Keyring()
        krg_memory = Keyring()

        for dim, key in keyring.items_values():
            if dim not in self.cs:
                continue
            infile = np.array(self.contains[dim][key])
            memory = np.arange(infile.size)

            none = np.where(np.equal(infile, None))[0]
            infile = np.delete(infile, none)
            memory = np.delete(memory, none)

            if len(infile) == 0:
                return None

            krg_infile[dim] = infile
            krg_memory[dim] = memory

        krg_infile.simplify()
        krg_memory.simplify()

        # Shared coordinates will suffer from a '.as_list' later on, we need
        # their parent size to be set.
        krg_infile.set_shape(self.cs)
        krg_memory.set_shape(self.db.scope.dims)

        msg = "Infile and memory Fg keyrings not shape equivalent."
        assert krg_infile.is_shape_equivalent(krg_memory), msg

        return CmdKeyrings(krg_infile, krg_memory)

    def get_commands(self, keyring: Keyring, memory: Keyring) -> List[Command]:
        """Get load commands.

        Recreate filenames from matches. Find in file indices for shared
        coordinates. Merge commands that have the same filename. If possible,
        merge contiguous shared keys.

        Add the keys for in coords. Favor integers
        and slices keys. Separate commands in different variables, order
        according to each variable dimensions order.

        :param keyring: Data to load, acting on this filegroup scope.
        :param memory: Corresponding memory keyring, acting on available scope.
        """
        if len(self.iter_shared(True)) == 0:
            commands = self._get_commands_no_shared()
        else:
            commands = self._get_commands_shared(keyring, memory)
            commands = command.merge_cmd_per_file(commands)

        krg_in_inf = self._get_keyring_in(keyring)
        krg_in_mem = memory.subset(self.iter_shared(False))

        for cmd in commands:
            cmd.join_filename(self.root)

            if len(cmd) > 0:
                cmd.merge_keys()
            else:
                cmd.append(Keyring(), Keyring())

            for keyrings in cmd:
                keyrings.modify(krg_in_inf, krg_in_mem)

            for krg_inf, krg_mem in cmd:
                krg_inf.make_list_int()
                krg_mem.make_list_int()

        commands = separate_variables(commands)

        for cmd in commands:
            for keyrings in cmd:
                self._process_infile(keyrings)

                # Need to access variables object with their name.
                keyrings.memory.make_idx_str(var=self.db.scope.var)

                self._sort_memory(keyrings)

                inf, mem = keyrings
                if not inf.is_shape_equivalent(mem.subset(inf)):
                    raise IndexError("Infile and memory keyrings have different"
                                     f" shapes ({cmd})")

        return commands

    def _process_infile(self, keyrings: CmdKeyrings):
        """Process infile keyring.

        Fetch order of dimensions of the data array in file using CS. If a
        dimension is in order but not in keyring, take first index.
        Remove None keys from keyring.

        Sort the infile keyring with the retrieved order. Additional keys
        not in the order are placed at the start of the keyring. It is the job
        of `load_cmd` to treat those appropriately (for example, variables).
        """
        key = self.cs['var'].in_idx.index(keyrings.infile['var'].value)
        order = self.cs['var'].dimensions[key]
        inf = keyrings.infile
        for dim in order:
            if dim not in keyrings.infile:
                log.warning("Additional dimension %s in file."
                            " Index 0 will be taken.", dim)
                key = 0
            else:
                key = keyrings.infile[dim]
            inf[dim] = key

            if inf[dim].type == 'none':
                raise KeyError(f"A None key was issued for '{dim}' "
                               "dimension which is present in file.")

        none_keys = [d for d, k in inf.items() if k.type == 'none']
        for d in none_keys:
            inf.pop(d)

        order = [d for d in inf if d not in order] + list(order)
        keyrings.set(inf.subset(order), keyrings.memory)

    def _sort_memory(self, keyrings: CmdKeyrings):
        """Sort keyrings according to each variables dimensions.

        This assume that variables have been separated (one variable per
        command). Remove keys not in the dimensions (except the variable key).
        """
        var = keyrings.memory['var'].value
        if var in self.db.variables:
            dims = self.db.variables[var].dims
            mem = keyrings.memory.subset(['var'] + dims)
            keyrings.set(keyrings.infile, mem)

    def _get_commands_no_shared(self) -> List[Command]:
        """Get commands when there are no shared coords."""
        cmd = command.Command()
        cmd.filename = ''.join(self.segments)
        return [cmd]

    def _get_commands_shared(self, keyring: Keyring,
                             memory: Keyring) -> List[Command]:
        """Return list of commands only with shared keys.

        :param keyring: Data to load, acting on this filegroup scope.
        :param memory: Corresponding memory keyring, acting on loaded scope.

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
                krgs_mem[name] = memory[name].as_list()[m[i_c]]

            cmd.append(krgs_inf, krgs_mem)
            commands.append(cmd)

        return commands

    def _get_commands_shared__get_info(
            self, keyring: Keyring) -> Tuple[List[List[List[str]]],
                                             List[List[int]],
                                             Union[List[int], None]]:
        """Retrieve matchers, regex index and in file index.

        Find matches and their regex indices for reconstructing filenames.
        Find the in-file indices as the same time.

        :param keyring: Data to load, acting on this filegroup scope.

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
            key = keyring[name]
            matches.append(key.apply(cs.matches, int2list=True))
            in_idxs.append(key.apply(cs.in_idx, int2list=True))
            rgx_idxs.append([rgx.idx for rgx in cs.matchers])
        return matches, rgx_idxs, in_idxs

    def _get_keyring_in(self, keyring: Keyring) -> Keyring:
        """Get the keys for in coordinates.

        :param keyring: Data to load, acting on this filegroup scope.
        """
        krg_inf = Keyring()
        for name, cs in self.iter_shared(False).items():
            krg_inf[name] = keyring[name].apply(cs.in_idx)
        krg_inf.simplify()
        return krg_inf

    def load_cmd(self, file: File, cmd: Command):
        """Load data from one file using a load command.

        Load content following a 'load command'.

        See :doc:`../filegroup` and :doc:`../expanding` for more information on
        how this function works, and how to implement it.

        :param file: Object to access file. The file is already opened by
            FilegroupScan.open_file().
        :param cmd: Load command.

        See also
        --------
        tomate.filegroup.filegroup_netcdf.FilegroupNetCDF.load_cmd:
            for an example
        """
        raise NotImplementedError

    def do_post_loading(self, keyring: Keyring):
        """Apply post loading functions."""
        var_loaded = keyring['var'].apply(self.cs['var'][:])
        for plf in self.post_loading_funcs:
            if plf.is_to_launch(var_loaded):
                plf.launch(self.db)

    def scan_variables_attributes(self):
        """Scan for variables specific attributes.

        Issues load commands to find for each variable a file in which it lies.
        For each command, use user defined function to scan attributes.
        Store them in VI.
        """
        def scan_attr(fg, file, infile, memory):
            attrs = {}
            for s in fg.scanners:
                if s.kind == 'var':
                    new = s.scan(fg, file, infile)
                    for name, value in new.items():
                        if name in attrs:
                            attrs[name].update(value)
                        else:
                            attrs[name] = value

            for name, [name_inf, values] in zip(memory, attrs.items()):
                log.debug("Found attributes (%s) for '%s' (%s infile)",
                          values.keys(), name, name_inf)
                fg.vi.set_attributes_default(name, **values)

        infile = Keyring(**{dim: 0 for dim in self.cs})
        infile['var'] = list(range(self.cs['var'].size))
        memory = infile.copy()
        memory['var'] = [i for i, d in enumerate(self.contains['var'])
                         if d is not None]
        cmds = self.get_commands(infile, memory)

        for cmd in cmds:
            file = self.open_file(cmd.filename, 'r', 'debug')
            try:
                log.debug('Scanning %s for variables specific attributes.', cmd.filename)

                for k in cmd:
                    k.memory.make_idx_str(var=self.cs['var'])
                infile = [v for k in cmd for v in k.infile['var']]
                memory = [v for k in cmd for v in k.memory['var']]
                scan_attr(self, file, infile, memory)

            except Exception:
                self.close_file(file)
                raise
            else:
                self.close_file(file)

    def _get_infile_name(self, var: str) -> str:
        """Get infile name."""
        cs = self.cs['var']
        if var in cs:
            return cs.in_idx[cs.get_str_index(var)]
        return var

    def write(self, filename: str, wd: str = None,
              file_kw: Dict = None, var_kw: Dict[str, Dict] = None,
              keyring: Keyring = None, **keys: KeyLike):
        """Write data to disk.

        The in-file variable name is the one specified in
        filegroup.cs['var'].in_idx if set, or the variable name passed as key.

        Variable specific arguments are passed to `netCDF.Dataset.createVariable
        <https://unidata.github.io/netcdf4-python/netCDF4/index.html
        #netCDF4.Dataset.createVariable>`__. If the 'datatype' argument is not
        specified, the 'datatype' attribute is looked in the VI, and if not
        defined, it is guessed from the numpy array dtype.

        If the 'fill_value' attribute is not specifed, the '_FillValue'
        attribute is looked in the VI, and if not defined
        `netCDF4.default_fillvals(datatype)` is used. It seems preferable to
        specify a fill_value rather than None.

        All attributes from the VariablesInfo are put in the file if their
        name do not start with an '_'.

        :param wd: Directory to place the file. If None, the filegroup root is
            used instead.
        :param file_kw: Keywords argument to pass to `open_file`.
        :param var_kw: Variables specific arguments. Keys are variables names,
            values are dictionnary containing options. Use '_all' to add an
            option for all variables.
        """
        if wd is None:
            wd = self.root
        filename = os.path.join(wd, filename)

        krg_mem = Keyring.get_default(keyring=keyring, **keys)
        krg_mem.set_default('var', slice(None))
        krg_mem.make_idx_str(var=self.db.loaded.var)

        cmd = Command()
        cmd.filename = filename
        krg_inf = Keyring(var=[self._get_infile_name(v)
                               for v in krg_mem['var']])

        cmd.append(krg_inf, krg_mem)
        cmd, = separate_variables([cmd])

        for keyrings in cmd:
            inf, mem = keyrings

            var = mem['var'].value
            cs = self.cs['var']
            dims = None
            if var in cs:
                key = cs.get_str_index(var)
                dims = cs.dimensions[key]
            if dims is None:
                dims = self.db.variables[var].dims

            mem.make_full(dims)
            mem.make_total()
            inf.make_full(dims)
            inf.make_total()
            inf.sort_by(['var'] + list(dims))

        if file_kw is None:
            file_kw = {}
        if var_kw is None:
            var_kw = {}

        file_kw.setdefault('mode', 'w')
        file_kw.setdefault('log_lvl', 'INFO')

        file = self.open_file(filename, **file_kw)
        try:
            self._write(file, cmd, var_kw)
        except Exception:
            self.close_file(file)
            raise
        else:
            self.close_file(file)

    def _write(self, file: File, cmd: Command, var_kw: Dict[str, Any]):
        """Write data in file.

        :param cmd: Memory acts on loaded scope.
        """
        raise NotImplementedError()

    def write_add_variable(self, var: str, sibling: str,
                           keyring: Keyring, kwargs: Dict = None) -> bool:
        """Add variable to files.

        Create load command to add variable to file.

        :param var: Variable to add.
        :param sibling: Variable along which to add.
        :param keyring: Part of data to write. On available scope.
        :param kwargs: Keyword arguments to pass for variable creation.
        """
        if kwargs is None:
            kwargs = {}

        keyring['var'] = self.db.avail.var.get_str_index(sibling)
        cmd = self.get_fg_keyrings(keyring)
        if cmd is None:
            return False

        commands = self.get_commands(*cmd)

        for cmd in commands:
            for cks in cmd:
                # keyring argument dictates command shape
                # help user to match `krg_inf` and `dimensions`
                for name, input_key in keyring.items():
                    if input_key.size == 0:
                        cks.infile[name].make_list_int()
                        cks.memory[name].make_list_int()
                    else:
                        cks.infile[name].make_int_list()
                        cks.memory[name].make_int_list()
                cks.memory['var'] = var
                cks.infile['var'] = self._get_infile_name(var)
            log.debug('Command: %s', cmd)

            file = self.open_file(cmd.filename, mode='r+', log_lvl='info')
            try:
                self.add_variables_to_file(file, cmd[0], **{var: kwargs})
            except Exception:
                self.close_file(file)
                raise
            else:
                self.close_file(file)

        return True

    def add_variables_to_file(self, file: File, cmd: Command, **kwargs):
        """Add variable to files."""
        raise NotImplementedError()
