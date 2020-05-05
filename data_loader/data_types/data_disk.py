"""Manage on-disk data."""

import numpy as np

import logging
import itertools
from typing import Dict, List, Union

from data_loader.coordinates.coord import Coord
from data_loader.custom_types import KeyLike, KeyLikeValue, KeyLikeVar
from data_loader.data_base import DataBase
from data_loader.filegroup.filegroup_load import FilegroupLoad, do_post_loading
from data_loader.keys.keyring import Keyring
from data_loader.scope import Scope
from data_loader.variables_info import VariablesInfo


log = logging.getLogger(__name__)


class DataDisk(DataBase):
    """Added functionalities for data on-disk.

    Scan metadata.
    Load data from disk.
    filegroups: List[FilegroupLoad]

    :param root: Root data directory containing all files.

    root: str
        Root data directory containing all files.
    post_loading_funcs: List[Tuple[Callable[DataBase]], KeyVar, bool, Dict[str, Any]]
        Functions applied after loading data.
    """
    def __init__(self, coords: List[Coord],
                 vi: VariablesInfo,
                 root: str,
                 filegroups: List[FilegroupLoad]):
        super().__init__(coords, vi)
        self.root = root

        self.filegroups = filegroups
        self.link_filegroups()

        self.allow_advanced = False

        self.post_loading_funcs = []

    def __str__(self):
        s = [super().__str__()]
        s.append("%d Filegroups:" % len(self.filegroups))
        s += ['\t%s' % ', '.join(fg.variables) for fg in self.filegroups]
        return '\n'.join(s)

    def link_filegroups(self):
        """Link filegroups and data."""
        for fg in self.filegroups:
            fg.db = self
            fg.acs = self.acs

    def load(self, *keys: KeyLike, **kw_keys: KeyLike):
        """Load part of data from disk into memory.

        What variables, and what part of the data
        corresponding to coordinates indices can be specified.
        Keys specified to subset data act on the available scope.
        If a parameter is None, all available is taken for that
        parameter.

        :param keys: [opt] What subset of coordinate to load.
            The order is that of self.coords.
        :param kw_keys: [opt] What subset of coordinate to load. Takes precedence
            over positional `coords`.
            Variables key argument should be named 'var'.

        Examples
        --------
        Load everything available

        >>> dt.load(None)

        Load first index of the first coordinate for the SST variable

        >>> dt.load("SST", 0)

        Load everything for SST and Chla variables.

        >>> dt.load(["SST", "Chla"], slice(None, None), None)

        Load time steps 0, 10, and 12 of all variables.

        >>> dt.load(None, time=[0, 10, 12])

        Load first index of the first coordinate, and a slice of lat
        for the SST variable.

        >>> dt.load("SST", 0, lat=slice(200, 400))
        """
        self.unload_data()

        kw_keys = self.get_kw_keys(*keys, **kw_keys)
        keyring = Keyring(**kw_keys)
        keyring.make_full(self.dims)
        keyring.make_total()
        keyring.make_int_list()
        keyring.make_var_idx(self.avail.var)
        keyring.sort_by(self.dims)

        self.loaded = self.get_subscope('avail', keyring)
        self.loaded.name = 'loaded'

        self.self_allocate(self.loaded.shape)

        loaded = any([fg.load_from_available(keyring)
                      for fg in self.filegroups])
        if not loaded:
            log.warning("Nothing loaded.")
        else:
            self.do_post_loading(keyring)

    def load_by_value(self, *keys: KeyLikeValue, by_day=False,
                      **kw_keys: KeyLikeValue):
        """Load part of data from disk into memory.

        Part of the data to load is specified by values.

        :param keys: [opt] Values to select for a coordinate.
            If is slice, use start and stop as boundaries. Step has no effect.
            If is float, int, or a list of, closest index for each value is taken.
        :param bool: Use `subset_by_day` for Time dimension rather than `subset`.
            Default to False.
        :param kw_keys: [opt] Same.

        Examples
        --------
        Load latitudes from 10N to 30N.
        >>> dt.load_by_value('SST', lat=slice(10, 30))

        Load latitudes from 5N to maximum available.
        >>> dt.load_by_value('SST', lat=slice(5, None))

        Load depth closest to 500.
        >>> dt.load_by_value(None, depth=500.)

        Load depths closest to 0, 10, 50
        >>> dt.load_by_value(None, depth=[0, 10, 50])
        """
        kw_keys = self.get_kw_keys(*keys, **kw_keys)
        scope = self.get_subscope_by_value('avail', int2list=True, by_day=by_day, **kw_keys)
        self.load_selected(scope=scope)

    def load_selected(self, keyring: Keyring = None,
                      scope: Union[str, Scope] = 'selected',
                      **keys: KeyLike):
        """Load data from a child scope of available.

        Subset is specified by a scope.
        The selection scope is expected to be created from
        the available one.

        :param keyring: [opt]
        :param scope: [opt] Selected scope created from available scope.
            Defaults to `self.selected`.
        :param keys: [opt]

        :raises KeyError: Selection scope is empty.
        :raises ValueError: Selection scope was not created from available.
        """
        scope = self.get_scope(scope)
        if scope.is_empty():
            raise KeyError("Selection scope is empty ('%s')." % scope.name)
        if scope.parent_scope != self.avail:
            raise ValueError("The parent scope is not the available data scope."
                             " (is '%s')" % scope.parent_scope.name)

        scope_ = scope.copy()
        scope_.slice(int2list=False, keyring=keyring, **keys)
        self.load(**scope_.parent_keyring.kw)

    def do_post_loading(self, keyring: Keyring):
        """Apply post loading functions."""
        do_post_loading(keyring['var'], self, self.avail.var,
                        self.post_loading_funcs)

    def write(self, filename: str, wd: str = None, **keys: KeyLike):
        """Write variables to disk.

        Write to a netcdf file.
        Coordinates are written too.

        :param filename: File to write in. Relative to each filegroup root
            directory, or from `wd` if specified.
        :param wd: [opt] Force to write `filename` in this directory.
        :param variables: [opt] Variables to write. If None, all are written.
        """
        keyring = Keyring(**keys)
        keyring.make_full(self.dims)
        keyring.make_total()
        keyring['var'] = self.loaded.var.get_var_names(keyring['var'])

        for fg in self.filegroups:
            variables = [v for v in keyring['var']
                         if v in fg.variables]
            if variables:
                keyring_fg = keyring.copy()
                keyring_fg['var'] = variables
                fg.write(filename, wd, keyring=keyring_fg)

    def write_add_variable(self, var: str, sibling: str,
                           inf_name: KeyLikeVar = None, **keys: KeyLike):
        """Add variables to files.

        :param var: Variable to add. Must be in loaded scope.
        :param sibling: Variable along which to add the data.
            New variable will be added to the same files
            and in same order.
        :param inf_name: [opt] Variable in-file name. Default to the variables name.
        :param keys: [opt] If a subpart of data is to be written.
            The selected data must match in shape that of the
            sibling data on disk.
        """
        if inf_name is None:
            inf_name = var
        scope = self.get_subscope('loaded', var=var, **keys)
        for fg in self.filegroups:
            if sibling in fg.variables:
                fg.write_add_variable(var, sibling, inf_name, scope)
                break

    def scan_variables_attributes(self):
        """Scan variables specific attributes.

        Filegroups should be functionnal for this.
        """
        for fg in self.filegroups:
            if 'var' in fg.scan_attr:
                fg.scan_variables_attributes()

    def scan_files(self):
        if not self.filegroups:
            raise RuntimeError("No filegroups in constructor.")
        for fg in self.filegroups:
            fg.scan_files()

    def compile_scanned(self):
        for fg in self.filegroups:
            fg.apply_coord_selection()
        values = self._get_coord_values()

        if not self.allow_advanced:
            self._get_intersection(values)
            self._apply_coord_values(values)
            for fg in self.filegroups:
                fg.find_contained(values)
        else:
            self._apply_coord_values(values)

        self.check_duplicates()


    def _get_coord_values(self) -> Dict[str, np.ndarray]:
        """Aggregate all available coordinate values.

        :returns: Values for each dimension.
        """
        values_c = {}
        for c in self.dims:
            values = []
            for fg in self.filegroups:
                if fg.cs[c].size is not None:
                    values += list(fg.cs[c][:])

            values = np.array(values)

            if values.size == 0:
                raise ValueError("No values found for %s in any filegroup." % c)

            if c != 'var':
                values.sort()
                duplicates = np.abs(np.diff(values)) < 1e-5
                values = np.delete(values, np.where(duplicates))

            values_c[c] = values
        return values_c

    def _get_intersection(self, values: Dict[str, np.ndarray]):
        """Get intersection of coordinate values.

        Only keep coordinates values common to all filegroups.
        The variables dimensions is excluded from this.
        Slice CoordScan and `contains` accordingly.

        :param values: All values available for each dimension.
            Modified in place to only values common
            accross filegroups.
        """
        for dim in self.coords:
            any_cut = False
            for fg in self.filegroups:
                none = np.equal(fg.contains[dim], None)
                rem = np.where(none)[0]
                sel = np.where(~none)[0]
                if rem.size > 0:
                    any_cut = True
                    self._slice_cs(dim, values, rem, sel)

            if any_cut:
                c = self.filegroups[0].cs[dim]
                log.warning("Common values taken for '%s', %d values ranging %s",
                            dim, c.size, c.get_extent_str())

    def _slice_cs(self, dim: str, values: np.ndarray,
                  remove: np.ndarray, select: np.ndarray):
        """Slice all CoordScan according to smaller values.

        :param dim: Dimension to slice.
        :param values: New values.
        :param remove: Indices to remove from available.
        :param select: Indices to keep in available.

        :raises IndexError: If no common values are found.
        """
        values[dim] = np.delete(values[dim], remove)
        for fg_ in self.filegroups:
            cs = fg_.cs[dim]
            if cs.size is not None:
                indices = fg_.contains[dim][select]
                indices = np.delete(indices,
                                    np.where(np.equal(indices, None))[0])
                if indices.size == 0:
                    raise IndexError("No common values for '%s'." % dim)

                if indices.size != cs.size:
                    log.warning("'%s' in %s will be cut: found %d values ranging %s",
                                dim, fg_.name, fg_.cs[dim].size,
                                fg_.cs[dim].get_extent_str())
                cs.slice(indices.astype(int))
            fg_.contains[dim] = np.delete(fg_.contains[dim], remove)

    def _apply_coord_values(self, values: Dict[str, np.ndarray]):
        """Set found values to master coordinates."""
        for dim, val in values.items():
            self.avail.dims[dim].update_values(val)

    def check_duplicates(self):
        """Check for duplicate data points.

        ie if a same data point (according to coordinate values)
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
                raise ValueError("Duplicate values in filegroups %s and %s"
                                 % (fg1.name, fg2.name))

    def check_regex(self):
        """Check if a pregex has been added where needed.

        :raises RuntimeError: If regex is empty and there is at least a out coordinate.
        """
        for fg in self.filegroups:
            coords = list(fg.iter_shared(True))
            if len(coords) > 0 and fg.regex == '':
                mess = ("Filegroup is missing a regex.\n"
                        "Contains: {0}\nCoordinates: {1}").format(
                            fg.name, coords)
                raise RuntimeError(mess)
