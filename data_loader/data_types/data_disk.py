"""Manage on-disk data."""

import logging
from typing import List, Union

from data_loader.custom_types import KeyLike, KeyLikeValue, KeyLikeVar
from data_loader.data_base import DataBase
from data_loader.filegroup.filegroup_load import FilegroupLoad, do_post_loading
from data_loader.keys.keyring import Keyring
from data_loader.scope import Scope


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
        self.post_loading_funcs = []

    def __str__(self):
        s = [super().__str__()]
        s.append("%d Filegroups:" % len(self.filegroups))
        s += ['\t%s' % ', '.join(fg.variables) for fg in self.filegroups]

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
