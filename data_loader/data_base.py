"""Base class for data.

Encapsulate data in a single numpy array, along with metadata,
such as coordinates, units, ...

Data is on disk and can be distributed in different files.

Data can be loaded onto ram using self.load_data.
Only a subset of data can be loaded.

Each implementation of the class can (and must) be tailored to a
a different data arrangement.

Contains
--------
Data

Routines
--------
merge_data(dt1, dt2)

change_variable()
"""

import logging
from typing import List

import numpy as np

from data_loader.coord import Coord
from data_loader.iter_dict import IterDict

log = logging.getLogger(__name__)


class DataBase():
    """Encapsulate data array and info about the variables.

    Data and coordinates can be accessed with subscript
    Data[{name of variable | name of coordinate}]

    Data is loaded from disk with load_data

    Parameters
    ----------
    root: str
        Data directory
    filegroups: List[Filegroup]
    vi: VariablesInfo
    *coords: List[Coord]

    Attributes
    ----------
    data: Numpy array
    filegroups: List[Filegroup]
        Filegroups
    _fg_idx: Dict[str, int]
        Index of filegroup for each variable
        {variable name: int}

    vi: VariablesInfo

    coords_name: List[str]
        Coordinates names
    coords: Dict[str, Coord]
        Coordinates by name
    dim: int
        Number of coordinates
    slices: Dict[NpIdx]
        Selected part of each coord

    shape: List[int]
        Shape of data
    """

    def __init__(self, root, filegroups, vi, *coords):
        self.root = root

        self._fg_idx = {}
        self.filegroups = filegroups
        for i, fg in enumerate(filegroups):
            for var in fg.contains:
                self._fg_idx.update({var: i})

        self.vi = vi
        self._vi_orr = vi.copy()

        names = [c.name for c in coords]
        coords_orr = IterDict(dict(zip(names, coords)))
        self.coords_name = names
        self._coords_orr = coords_orr
        self.coords = self.get_coords_from_backup()
        self.dim = len(coords)
        self.slices = dict(zip(self.coords_name,
                               [slice(0, i, 1) for i in range(self.dim)]))

        self.data = None

        self.link_filegroups()

        self.do_post_load_user = None

    def __getitem__(self, y):
        """Return slice of data or variable, or coordinate.

        If y is a coordinate name, return the coordinate.
        If y is a variable name, return the corresponding data slice.
        Else, it is transmitted to data.__getitem__()

        Parameters
        ----------
        y: str or NpIdx

        Raises
        ------
        KeyError:
            If key is string and not a coordinate or variable
        """
        if isinstance(y, str):
            if y in self.vi.var:
                y = self.vi.idx[y]
            elif y in self.coords_name:
                return self.coords[y]
            else:
                raise KeyError("Key '%s' not in coordinates or variables" % y)

        return self.data[y]

    def iter_slices(self, coord, size_slice=1, c_slice=None):
        """Iter through data with slices of `coord` of size `n_iter`.

        Parameters
        ----------
        coord: str
            Coordinate to iterate along to
        size_slice: int, optional
            Size of the slices to take
        c_slice: Slice, optional
            A subset of the full available coordinate to iter through
        """
        if c_slice is None:
            c_slice = slice(None, None)

        c = self.get_coords_from_backup(coord)[coord]
        c.slice(c_slice)

        n_slices = int(np.ceil(c.size / size_slice))
        slices = []
        for i in range(n_slices):
            start = i*size_slice
            stop = min((i+1)*size_slice, c.size)
            slices.append(slice(start, stop))

        return slices

    def link_filegroups(self):
        """Link filegroups and data."""
        for fg in self.filegroups:
            fg.db = self

    def get_coords_from_backup(self, *coords):
        """Remake coordinates from backup.

        Parameters
        ----------
        *coords: List of str
            Coord to select

        Returns
        -------
        coords: IterDict[Coord]
        """
        if not coords:
            coords = self.coords_name
        coords_orr = [self._coords_orr[name] for name in coords]
        copy = [c.copy() for c in coords_orr]
        coords = IterDict(dict(zip(coords, copy)))
        return coords

    @property
    def shape(self) -> List[int]:
        """Shape of the data."""
        return [self.vi.n] + [c.size for c in self.coords.values()]

    def get_coord(self, name: str) -> Coord:
        """Return Coord with name.

        Search within alternative names.

        Raises
        ------
        KeyError
            If the name is not found.
        """
        # First check name
        for c_name, coord in self.coords.items():
            if c_name == name:
                return coord

        # Then check name_alt
        for c_name, coord in self.coords.items():
            if name in coord.name_alt:
                return coord

        raise KeyError(str(name) + " not found")

    def get_limits(self, *coords, order=False):
        """Return limits of coordinates.

        Parameters
        ----------
        coords: List[str]
            Coordinates name.
            If none, defaults to all coords, in the order
            of data.
        order: str, optional
            Sort output for descending coordinates.

        Returns
        -------
        limits: List[[float, float]]
            First and last values (extent) of each coordinate.
            If `order`, the min and max values are returned
            instead.

        Examples
        --------
            dt.get_lim() = [[first, last], [first, last], ...]
            dt.get_lim("time", order=True) = [[min, max]]
        """
        if not coords:
            coords = [c.name for c in self.coords.values()]

        limits = []
        for c in coords:
            lim = self[c].get_extent()
            if order:
                lim.sort()
            limits.append(lim)
        return limits

    def get_extent(self, *coords, order=False):
        """Return extent of coordinates.

        A flatened version of get_limits.

        Parameters
        ----------
        coords: List[str]
            Coordinates name.
            If none, defaults to all coords, in the order
            of data.
        order: str, optional
            Sort output for descending coordinates.

        Returns
        -------
        limits: List[float]
            First and last values (extent) of each coordinate.
            If `order`, the min and max values are returned
            instead.

        Examples
        --------
            dt.get_lim() = [first, last, first, last, ...]
            dt.get_lim("time", order=True) = [min, max]
        """
        limits = self.get_limits(*coords, order=order)
        extent = []
        for lim in limits:
            extent += lim
        return extent

    def get_coords_kwargs(self, *coords, **kw_coords):
        """Make standard, full kwargs.

        From a mix of positional and keyword argument,
        make a list of keywords, containing all coords.
        Missing coord key is taken as slice(None, None).

        Parameters
        ----------
        coords: List[NpIdx]
            Key for subsetting coordinates, position is that
            of self.coords.
        kw_coords: Dict[NpIdx]
            Key for subsetting coordinates.

        Exemples
        --------
        self.get_coords_kwargs([0, 1], lat=slice(0, 10))
        """

        if not coords:
            coords = []

        if not kw_coords:
            kw_coords = {}

        for i, key in enumerate(coords):
            kw_coords.update({self.coords_name[i]: key})

        for coord in self.coords_name:
            if coord not in kw_coords:
                kw_coords[coord] = slice(None, None)

        return kw_coords

    def fix_kw_coords(self, kw_coords, backup=True):
        """Avoid slices with None attributes."""
        for name, key in kw_coords.items():
            if isinstance(key, slice):
                kw_coords[name] = self.fix_slice(key, backup, name)

        return kw_coords

    def fix_slice(self, slc, backup=True, coord=None, size=None):
        """Avoid slices with None attributes.

        Coordinates size is used (backup or not)
        If size is specified, use that instead.

        Parameters
        ----------
        slc: slice
        backup: bool
            If the size of the coordinates has to be taken
            from coordinate backup.
        size: int
            Force the size to be used.
        """
        if size is None:
            if backup:
                c = self.get_coords_from_backup(coord)[coord]
            else:
                c = self.coords[coord]
            size = c.size

        return slice(*slc.indices(size))

    def sort_by_coords(self, dic):
        # TODO: review
        """Sort dictionnary.

        The order is that of `self.coords_name`.
        """
        keys = {}
        for key, value in dic.items():
            c = self.get_coord(key)
            keys[c.name] = [key, value]

        keys_ord = {}
        for name in self.coords_name:
            key, value = keys[name]
            keys_ord[key] = value

        return keys_ord

    def set_slice(self, variables=None, **kw_coords):
        """Pre-select variables and coordinates slices.

        Selection is applied to available coordinates.
        Should be used only if data is not loaded,
        otherwise use `slice_data`.

        This selection is reset when using self.load_data.
        """
        if self.data is not None:
            log.warning("Using set_coords_slice with data loaded can decouple "
                        "data and coords. Use slice_data instead.")
        if variables is None:
            variables = self._vi_orr.var
        kw_coords = self.get_coords_kwargs(**kw_coords)
        kw_coords = self.fix_kw_coords(kw_coords, backup=True)

        self.vi = self._vi_orr[variables]

        coords = self.get_coords_from_backup()
        for name, key in kw_coords.items():
            coords[name].slice(key)
            self.slices[name] = key
        self.coords = coords

    def slice_data(self, variables=None, **kw_coords):
        """Select a subset of loaded data and coords."""
        if variables is None:
            variables = self.vi.var
        variables = [self.vi.idx[var] for var in variables]
        kw_coords = self.get_coords_kwargs(**kw_coords)
        kw_coords = self.fix_kw_coords(kw_coords, backup=False)
        kw_coords = self.sort_by_coords(kw_coords)

        for name, key in kw_coords.items():
            c = self.coords[name]
            c.slice(key)
            self.slices[name] = subset_slices(self.slices[name], key)

        if self.data is not None:
            keys = variables + list(kw_coords.values())
            self.data = self.data[tuple(keys)]

    def load_data(self, var_load, *coords, **kw_coords):
        """Load part of data from disk into memory.

        What variables, and what part of the data
        corresponding to coordinates indices can be specified.

        Parameters
        ----------
        var_load: str or List[str]
            Variables to load. If None, all variables available
            are taken.
        *coords: List[NpIdx]
            What subset of coordinate to load. The order is that
            of self.coords.
        **kw_coords: Dict[coord name, NpIdx]
            What subset of coordinate to load. Takes precedence
            over `coords`.

        Raises
        ------
        ValueError:
            If key is other than integer, list of integer, or slice

        Examples
        --------
        Load everything available
        dt.load_data(None)

        Load first index of the first coordinate for the SST variable
        dt.load_data("SST", 0)

        Load everything for SST and Chla variables.
        dt.load_data(["SST", "Chla"], slice(None, None), None)

        Load time steps 0, 10, and 12 of all variables.
        dt.load_data(None, time=[0, 10, 12])

        Load first index of the first coordinate, and a slice of lat
        for the SST variable.
        dt.load_data("SST", 0, lat=slice(200, 400))
        """
        kw_coords = self.get_coords_kwargs(*coords, **kw_coords)
        kw_coords = self.fix_kw_coords(kw_coords, backup=True)
        kw_coords = self.sort_by_coords(kw_coords)

        for name, key in kw_coords.items():
            reject = not isinstance(key, (int, slice))
            if isinstance(key, (list, tuple)):
                reject = not all(isinstance(z, int) for z in key)
            if reject:
                raise ValueError("'%s' key is not an integer, list of integers, or slice"
                                 " (is %s)" % (name, type(key)))

        if var_load is None:
            var_load = slice(None, None, None)

        for coord, key in kw_coords.items():
            if isinstance(key, int):
                kw_coords[coord] = [key]

        self.set_slice(variables=var_load, **kw_coords)
        self.allocate_memory()
        self._load_data(self.vi.var, kw_coords)
        self.do_post_load()

    def _find_shape(self, kw_coords) -> List[int]:
        """Find the shape of the data to load.

        Excluding the number of variables.

        Parameters
        ----------
        kw_coords: Dict[coord: str, key: NpIdx]
            Asked index for each coord, not in order
        """
        shape = [0 for _ in range(self.dim)]
        for coord, key in kw_coords.items():
            i = self.coords_name.index(coord)
            if isinstance(key, list):
                shape[i] = len(key)
            elif isinstance(key, slice):
                shape[i] = len(range(*key.indices(self.shape[i+1])))

        return shape

    def allocate_memory(self):
        """Allocate data member."""
        log.info("allocating numpy array of shape %s", self.shape)
        self.data = np.zeros(self.shape)

    def _get_filegroups_for_variables(self, variables):
        """Find the filegroups corresponding to variables.

        Parameters
        ----------
        variables: List of str

        Returns
        -------
        fg_var: [[Filegroup, List of str]]
            A list of the filegroups with the corresponding variables
        """

        # find the filegroups we need to load
        fg_var = []
        for var in variables:
            fg = self.filegroups[self._fg_idx[var]]
            try:
                idx = [z[0] for z in fg_var].index(fg)
            except ValueError:
                fg_var.append([fg, []])
                idx = -1
            fg_var[idx][1].append(var)

        return fg_var

    def _load_data(self, var_list, keys):
        # TODO: kwargs
        """Load data.

        Parameters
        ----------
        varList: List[str] or str
            Passed to VariablesInfo.__getitem__
        keys: Dict[coord name, key]
            Passed to Coord.__getitem__
        """
        fg_var = self._get_filegroups_for_variables(var_list)

        for fg, variables in fg_var:
            fg.load_data(variables, keys)

    def set_post_load_func(self, func):
        """Set function for post loading treatements.

        Parameters
        ----------
        func: Callable[DataBase]
        """
        self.do_post_load_user = func

    def do_post_load(self):
        """Do post loading treatments."""
        if callable(self.do_post_load_user):
            self.do_post_load_user(self)

    def set_data(self, var, data):
        """Set the data for a single variable."""

        data = np.expand_dims(data, 0)

        if self.data is None:
            self.data = data
            self.vi = self._vi_orr[var]
        elif var in self.vi.var:
            self[var][:] = data[0]
        else:
            self.vi = self._vi_orr[self.vi.var + [var]]
            self.data = np.concatenate((self.data, data), axis=0)

    def add_variable(self, variables, data, infos):
        """Concatenante new_data to data, and add kwargs to vi.

        Parameters
        ----------
        variables: List[str]
            Variables to add
        data: Array
            Corresponding data
        infos: List[Dict[name: str, Any]]
            Passed to VariablesInfo.add_variable
        """
        self.vi.add_variable(variables, infos)

        if self.data is not None:
            self.data = np.ma.concatenate((self.data, data), axis=0)
        else:
            self.data = data
            self.vi = self.vi[variables]

    def pop_variables(self, variables: List[str]):
        """Remove variables from data and vi."""
        if not isinstance(variables, (list, tuple)):
            variables = [variables]

        keys = self.vi.idx[variables]
        if self.data is not None:
            self.data = np.delete(self.data, [keys], axis=0)
        self.vi.pop_variables(variables)

    def write(self, filename, wd=None, variables=None, **kwcoords):
        """Write variables to disk.

        Write to a netcdf file.
        Coordinates are written too.

        Parameters
        ----------
        wd: str
            Directory. If None, `self.root` is used.
        variables: Union[List[str], str]
        filename: str
            If None, the first value of time is used.
        """
        if wd is None:
            wd = self.root

        if variables is None:
            variables = self.vi.var

        keys = self.get_coords_kwargs(**kwcoords)

        fg_var = self._get_filegroups_for_variables(variables)

        for fg, var_list in fg_var:
            fg.write(filename, wd, var_list, keys)


def subset_slices(key, key_subset):
    """Return slice when subsetting a coord.

    Parameters
    ----------
    key: Slice or List
        Current slice of a coordinate
    key_subset: Slice or List
        Asked slice of coordinate
    """
    key_new = None
    if isinstance(key, list):
        if isinstance(key_subset, slice):
            key_new = key[key_subset]
        if isinstance(key_subset, list):
            key_new = [key[i] for i in key_subset]

    if isinstance(key, slice):
        if isinstance(key_subset, slice):
            key_new = slice(key_subset.start + key.start,
                            key_subset.stop + key.start,
                            key_subset.step * key.step)
        if isinstance(key_subset, list):
            key_new = [i*key.step + key.start for i in key_subset]

    return key_new
