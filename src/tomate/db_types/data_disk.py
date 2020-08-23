"""Manage on-disk data."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import logging
import itertools
from typing import Any, Dict, List, Type, Union

import numpy as np

from tomate.coordinates.coord import Coord
from tomate.custom_types import KeyLike, KeyLikeValue
from tomate.data_base import DataBase
from tomate.filegroup.filegroup_load import FilegroupLoad
from tomate.filegroup.filegroup_scan import make_filegroup
from tomate.filegroup.spec import CoordScanSpec
from tomate.keys.keyring import Keyring
from tomate.scope import Scope
from tomate.variables_info import VariablesInfo


log = logging.getLogger(__name__)


class DataDisk(DataBase):
    """Added functionalities for on-disk data management.

    Files are regrouped in Filegroups object, treated independently.
    DataDisk act as a director for those filegroups. It starts
    the scanning process, compile information found in different
    filegroups, and initiate loading and writing data from / to disk.

    :param dims: Dimensions (ie subclasses of Coord). This includes variables.
        The dimensions will be stored in various scopes in the order they
        are supplied. This same order is used in many methods when specifying
        keys. They are linked (not copied) to the available scope.
    :param vi: [opt] Information on the variables and data.
        If None, one is created.
    :param root: Root data directory containing all files.

    :attr root: str: Root data directory containing all files.
    :attr filegroups: List[FilegroupLoad]: List of filegroups.
    :attr allow_advanced: bool: If allows advanced data arrangement.
    :attr post_loading_funcs: List[PostLoadingFunc]: Functions applied
        after loading data.
    """

    CSS = CoordScanSpec

    def __init__(self, dims: List[Coord],
                 root: str, filegroups: List[FilegroupLoad],
                 vi: VariablesInfo = None):
        super().__init__(dims, vi)
        self.root = root

        self.var_disk = set(self.avail.var)

        self.filegroups = filegroups
        for fg in self.filegroups:
            fg.db = self

        self.allow_advanced = False

        self.post_loading_funcs = []

    def __repr__(self):
        s = [super().__repr__()]
        s.append("{} Filegroups:".format(len(self.filegroups)))
        s += ['\t{}: {}'.format(fg.name, ', '.join(fg.variables))
              for fg in self.filegroups]
        return '\n'.join(s)

    def get_filegroup(self, key: Union[int, str]) -> FilegroupLoad:
        """Get filegroup by index or name."""
        if isinstance(key, int):
            return self.filegroups[key]
        if isinstance(key, str):
            fgs = [fg for fg in self.filegroups
                   if fg.name == key]
            if len(fgs) == 0:
                raise KeyError(f"No filegroup with name {key}")
            if len(fgs) > 1:
                raise IndexError(f"More than one filegroup with name {key}")
            return fgs[0]
        raise TypeError("Key must be filegroup index or name (is {})"
                        .format(type(key)))

    def add_filegroup(self, fg_type: Type, coords_fg: List[CoordScanSpec],
                      name: str = '', root: str = None,
                      variables_shared: bool = False, **kwargs: Any):
        """Add filegroup to database.

        See :func:`Constructor.add_filegroup
        <tomate.constructor.Contructor.add_filegroup>` for details.
        """
        fg = make_filegroup(fg_type, self.root, self.avail.dims,
                            coords_fg, self.vi, root, name,
                            variables_shared, **kwargs)
        fg.db = self
        self.filegroups.append(fg)

    def load(self, *keys: KeyLike, **kw_keys: KeyLike):
        """Load part of data from disk into memory.

        Unload all data previously loaded, and load other data from disk.
        Keys specified to subset data act on the available scope.
        If a dimension is omitted or None, all available values are loaded.

        :param keys: [opt] Part of each dimension to load, specified in the same
            order as in the database. Can be integers, list of integers, slices,
            or None. For string coordinates (variables for instance), can also
            be strings or list of strings.
        :param kw_keys: [opt] Same as `keys`, takes precedence over it.
            Key for variables should be named 'var'.

        Examples
        --------
        Load everything available

        >>> db.load(None)

        Load first index of the first coordinate for the SST variable

        >>> db.load("SST", 0)

        Load everything for SST and Chla variables.

        >>> db.load(["SST", "Chla"], slice(None, None), None)

        Load time steps 0, 10, and 12 of all variables.

        >>> db.load(None, time=[0, 10, 12])

        Load first index of the first coordinate, and a slice of lat
        for the SST variable.

        >>> db.load("SST", 0, lat=slice(200, 400))
        """
        self.unload()

        kw_keys = self.get_kw_keys(*keys, **kw_keys)
        keyring = Keyring(**kw_keys)
        keyring.make_full(self.dims)
        keyring.make_total()
        keyring.make_str_idx(**self.avail.dims)

        self.loaded = self.get_subscope('avail', keyring, name='loaded')
        self.remove_loaded_variables([v for v in self.loaded
                                      if v not in self.var_disk])

        for var in self.loaded.var:
            self.variables[var].allocate()

        loaded = [fg.load_from_available(self.loaded.parent_keyring)
                  for fg in self.filegroups]
        if not any(loaded):
            log.warning("Nothing loaded.")
        else:
            self.do_post_loading()

    def load_by_value(self, *keys: KeyLikeValue, by_day=False,
                      **kw_keys: KeyLikeValue):
        """Load part of data from disk into memory.

        Part of the data to load is specified by values or index.

        :param keys: [opt] Values to load for each dimension, in the same order
            as in the database. If is slice, use start and stop as boundaries.
            Step has no effect. If is float, int, or a list of, closest index
            for each value is taken. Act on loaded scope.
        :param by_day: If True, find indices prioritising dates.
            See :ref:`Some examples of coordinates subclasses` for details.
        :param kw_keys: [opt] Values to load for each dimension. Argument name
            is dimension name, argument value is similar to `keys`, and take
            precedence over it. Argument name can also be a dimension name
            appended with `_idx`, in which case the selection is made by index
            instead. Value selection has priority.

        Examples
        --------
        Load latitudes from 10N to 30N.

        >>> db.load_by_value('SST', lat=slice(10., 30.))

        Load latitudes from 5N to maximum available.

        >>> db.load_by_value('SST', lat=slice(5, None))

        Load depth closest to 500 and first time index.

        >>> db.load_by_value(depth=500., time_idx=0)

        Load depths closest to 0, 10, 50

        >>> db.load_by_value(depth=[0, 10, 50])

        See also
        --------
        load
        """
        kw_keys = self.get_kw_keys(*keys, **kw_keys)
        scope = self.get_subscope_by_value('avail', int2list=True,
                                           by_day=by_day, **kw_keys)
        self.load_selected(scope=scope)

    def load_selected(self, keyring: Keyring = None,
                      scope: Union[str, Scope] = 'selected',
                      **keys: KeyLike):
        """Load data from the selected scope.

        Selection has to have been made from the available scope.

        :param keys: [opt] Slice the selection further. Keys act on
            `scope`.
        :param scope: [opt] Any scope created from available scope, defaults
             to selected scope.
        :param keyring: [opt]

        :raises KeyError: Selection scope is empty.
        :raises ValueError: Selection scope was not created from available.
        """
        scope = self.get_scope(scope)
        if scope.is_empty():
            raise KeyError(f"Selection scope is empty ('{scope.name}').")
        if scope.parent_scope != self.avail:
            raise ValueError("The parent scope is not the available data scope."
                             " (is '{}')".format(scope.parent_scope.name))

        scope_ = scope.copy()
        scope_.slice(int2list=False, keyring=keyring, **keys)
        self.load(**scope_.parent_keyring.kw)

    def do_post_loading(self):
        """Apply post loading functions."""
        var_loaded = self.loaded.var[:]
        for po in self.post_loading_funcs:
            if po.is_to_launch(var_loaded):
                po.launch(self)

    def write(self, filename: str, directory: str = None,
              file_kw: Dict = None, var_kw: Dict[str, Dict] = None,
              **keys: KeyLike):
        """Write data and metadata to disk.

        If a variable to write is contained in multiple filegroups,
        only the first filegroup will be used to write this variable.

        To find with what filegroup to write each variable, the variable
        CoordScan should be set up correctly. Otherwise one can use
        filegroup.write() directly.

        Essentially a wrapper around :func:`FilegroupLoad.write
        <tomate.filegroup.filegroup_load.FilegroupLoad.write>`, see for
        more details on arguments.

        :param filename: File to write. Relative to each filegroup root
            directory, or from `wd` if specified.
        :param directory: [opt] Force to write `filename` in this directory
            instead of each filegroups root.
        :param file_kw: Keywords argument to pass to `open_file`.
        :param var_kw: Variables specific arguments.
        :param keys: [opt] Only write a subpart of loaded data.
        """
        keyring = Keyring(**keys)
        keyring.make_full(self.dims)
        keyring.make_total()
        keyring.make_str_idx(**self.loaded.dims)

        variables = self.loaded.var.get_str_names(keyring['var'].no_int())

        for fg in self.filegroups:
            variables_fg = [v for v in variables if v in fg.variables]
            for v in variables_fg:
                variables.remove(v)
            if variables_fg:
                keyring_fg = keyring.copy()
                keyring_fg['var'] = variables_fg
                fg.write(filename, directory, keyring=keyring_fg,
                         file_kw=file_kw, var_kw=var_kw)

    def write_add_variable(self, var: str, sibling: str,
                           kwargs: Dict = None, **keys: KeyLike):
        """Add variable to existing files.

        Add a variable to the same files of another variable.

        :param var: Variable to add. Must be in loaded scope.
        :param sibling: Variable along which to add the data. New variable will
            be added to the same files and in same order.
        :param keys: [opt] If a subpart of data is to be written. The selected
            data must match in shape that of the sibling data on disk.
        """
        scope = self.loaded.copy()
        scope.slice(**keys, int2list=False)
        for fg in self.filegroups:
            fg.write_add_variable(var, sibling, scope.parent_keyring,
                                  kwargs=kwargs)

    def scan_variables_attributes(self):
        """Scan variables specific attributes.

        In each filegroup, emit a load command to locate one file for each
        variable.
        """
        for fg in self.filegroups:
            if any(s.kind == 'var' for s in fg.scanners):
                fg.scan_variables_attributes()

    def scan_files(self):
        """Scan files for metadata.

        :raises IndexError: If no filegroups in database.
        """
        if not self.filegroups:
            raise IndexError("No filegroups in database.")
        self.check_regex()
        self.check_scanning_functions()
        for fg in self.filegroups:
            fg.scan_files()

    def compile_scanned(self):
        """Compile metadata scanned.

        -Apply CoordScan selections.
        -Aggregate coordinate values from all filegroups.
        -If advanced data organization is not allowed, only keep intersection.
        -Apply coordinates values to available scope.
        """
        if len(self.filegroups) == 1:
            fg = self.filegroups[0]
            fg.apply_coord_selection()
            values = {d: fg.cs[d][:] for d in fg.cs}
            self._apply_coord_values(values)
            for cs in fg.cs.values():
                cs.contains = np.arange(cs.size)
        else:
            for fg in self.filegroups:
                fg.apply_coord_selection()
            values = self._get_coord_values()
            self._find_contained(values)

            if not self.allow_advanced:
                self._get_intersection(values)
                self._find_contained(values)

            self.check_duplicates()
            self._apply_coord_values(values)

    def _find_contained(self, values: Dict[str, np.ndarray]):
        """Find what part of available are contained in each fg."""
        for fg in self.filegroups:
            for dim in fg.cs:
                fg.cs[dim].find_contained(values[dim])

    def _get_coord_values(self) -> Dict[str, np.ndarray]:
        """Aggregate all available coordinate values.

        :returns: Values for each dimension.
        :raises ValueError: No values found for one of the coordinate.
        """
        values_c = {}
        for c in self.dims:
            values = []
            for fg in self.filegroups:
                if c in fg.cs and fg.cs[c].size is not None:
                    values += list(fg.cs[c][:])

            values = np.array(values)

            if values.size == 0:
                raise ValueError(f"No values found for {c} in any filegroup.")

            if c != 'var':
                values.sort()
                threshold = max([fg.cs[c].float_comparison
                                 for fg in self.filegroups
                                 if c in fg.cs])
                duplicates = np.abs(np.diff(values)) < threshold
                if np.any(duplicates):
                    log.debug("Removing duplicates in available '%s' values"
                              " using float threshold %s", c, threshold)
                values = np.delete(values, np.where(duplicates))

            values_c[c] = values
        return values_c

    def _get_intersection(self, values: Dict[str, np.ndarray]):
        """Get intersection of coordinate values.

        Only keep coordinates values common to all filegroups. The variables
        dimensions is excluded from this. Slice CoordScan and `contains`
        accordingly.

        :param values: All values available for each dimension. Modified in
            place to only values common accross filegroups.
        """
        for dim in self.coords:
            none = np.zeros(values[dim].size, bool)
            for fg in self.filegroups:
                if dim in fg.cs:
                    none |= np.equal(fg.contains[dim], None)
            if np.any(none):
                values[dim] = np.delete(values[dim], np.where(none))
                sel = np.where(~none)[0]
                for fg in self.filegroups:
                    if dim not in fg.cs:
                        continue
                    cs = fg.cs[dim]
                    size, extent = cs.size, cs.get_extent_str()
                    if cs.slice_from_avail(sel):
                        log.warning("'%s' in '%s' will be cut: "
                                    "found %d values ranging %s",
                                    dim, fg.name, size, extent)
                        if cs.size == 0:
                            for fg_ in self.filegroups:
                                if fg != fg_:
                                    log.warning("'%s' in '%s': found %d values"
                                                " ranging %s", dim, fg_.name,
                                                fg_.cs[dim].size,
                                                fg_.cs[dim].get_extent_str())
                            raise IndexError(f"No common values for '{dim}'")

                cs = self.filegroups[0].cs[dim]
                log.warning("Common values taken for '%s', "
                            "%d values ranging %s.",
                            dim, cs.size, cs.get_extent_str())

    def _apply_coord_values(self, values: Dict[str, np.ndarray]):
        """Set found values to master coordinates."""
        for dim, val in values.items():
            self.avail.dims[dim].update_values(val)

    def check_duplicates(self):
        """Check for duplicate data points.

        *ie* if a same data point (according to coordinate values)
        can be found in two filegroups.

        :raises ValueError: If there is a duplicate.
        """
        for fg1, fg2 in itertools.combinations(self.filegroups, 2):
            intersect = []
            for c1, c2 in zip(fg1.contains.values(), fg2.contains.values()):
                w1 = np.where(~np.equal(c1, None))[0]
                w2 = np.where(~np.equal(c2, None))[0]
                intersect.append(np.intersect1d(w1, w2).size)
            if all(s > 0 for s in intersect):
                raise ValueError("Duplicate values in filegroups {} and {}"
                                 .format(fg1.name, fg2.name))

    def check_regex(self):
        """Check if a pregex has been added where needed.

        :raises AttributeError: If regex is empty and there is at
            least one shared coordinate.
        """
        for fg in self.filegroups:
            coords = list(fg.iter_shared(True))
            if len(coords) > 0 and fg.regex == '':
                raise AttributeError(f"Filegroup '{fg.name}' is missing a regex.")

    def check_scanning_functions(self):
        """Check if CoordScan have scanning functions set.

        :raises KeyError: One coordinate is missing a scanning function.
        """
        for fg in self.filegroups:
            for name, cs in fg.cs.items():
                for elt in cs.elts:
                    if (elt not in cs.manual
                            and not any(elt in s.returns for s in cs.scanners)
                            and elt not in cs.fixed_elts):
                        raise KeyError("Element '{}' of coordinate '{}' in"
                                       " filegroup '{}' has no scanning function"
                                       " set and was not given values manually"
                                       .format(elt, name, fg.name))
