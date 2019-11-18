"""Abstract base class for data.

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

from types import MethodType
from typing import List

import os
import numpy as np

from data_loader.coord import Coord
from data_loader.variables_info import VariablesInfo
from data_loader.iter_dict import IterDict


class _DataBase():
    # TODO: slice by value
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
    fg_idx: Dict[str, int]
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

        self.fg_idx = {}
        self.filegroups = filegroups
        for i, fg in enumerate(filegroups):
            for var in fg.contains:
                self.fg_idx.update({var: i})

        self.vi = vi
        self._vi_orr = vi.copy()

        names, coords_orr = self._get_coords(coords)
        self.coords_name = names
        self._coords_orr = coords_orr
        self.coords = self.get_coords_from_backup()
        self.dim = len(coords)
        self.slices = dict(zip(self.coords_name,
                               [slice(None, None) for _ in range(self.dim)]))

        self.data = None

    def __getitem__(self, y):
        """Return slice of data or variable, or coordinate.

        If y is a coordinate name, return the coordinate.
        If y is a variable name, return the corresponding data slice.
        Else, it is transmitted to data.__getitem__()

        Parameters
        ----------
        y: str or NpIdx
        """
        if isinstance(y, str):
            if y in self.coords_name:
                return self.coords[y]
            if y in self.vi.var:
                y = self.vi.idx[y]

        return self.data[y]

    def _get_coords(self, coords):
        """Make an IterDict from a list of coords.

        Parameters
        ----------
        coords: List[Coord]

        Returns
        -------
        coords: IterDict[Coord]
        """
        names = [c.name for c in coords]
        coords = IterDict(dict(zip(names, coords)))
        return names, coords

    def get_coords_from_backup(self):
        """Remake coordinates from backup.

        Returns
        -------
        coords: IterDict[Coord]
        """
        coords_orr = self._coords_orr.values()
        copy = [c.copy() for c in coords_orr]
        _, coords = self._get_coords(copy)
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

    def _get_coords_kwargs(self, *coords, **kw_coords):
        """Make standard, full kwargs.

        From a mix of positional and keyword argument,
        make a list of keywords, containing all coords.
        Missing coord key is taken as None.
        Are ordered as in self.coords

        Parameters
        ----------
        coords: List[NpIdx]
            Key for subsetting coordinates, position is that
            of self.coords.
        kw_coords: Dict[NpIdx]
            Key for subsetting coordinates.

        Exemples
        --------
        self._get_coords_kwargs([0, 1], lat=slice(0, 10))
        """

        if not coords:
            coords = []

        if not kw_coords:
            kw_coords = {}

        for i, key in enumerate(coords):
            kw_coords.update({self.coords_name[i]: key})

        for coord in self.coords_name:
            if coord not in kw_coords:
                kw_coords.update({coord: slice(None, None)})

        kw_coords = self._sort_by_coords(kw_coords)

        return kw_coords

    def _sort_by_coords(self, dic):
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

    def _slice_data(self, variables, **kw_coords):
        """Slice data and coordinates by index."""
        if self.data is not None:
            key = tuple([variables] + list(kw_coords.values()))
            self.data = self.data[key]

    def slice_data(self, variables=None, *coords, **kw_coords):
        """Slice data and coordinates by index."""
        if variables is None:
            variables = slice(None, None)
        kw_coords = self._get_coords_kwargs(*coords, **kw_coords)

        self._slice_data(variables, **kw_coords)

    def _slice_coords(self, **kw_coords):
        """Slice coordinates by index.

        This slice is reset if data is reloaded.
        """
        for name, key in kw_coords.items():
            self.coords[name].slice(key)

        self.slices = kw_coords

    def slice_coords(self, *coords, **kw_coords):
        """Slice coordinates by index.

        This slice is reset if data is reloaded.
        """
        kw_coords = self._get_coords_kwargs(*coords, **kw_coords)
        self._slice_coords(**kw_coords)

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

        kw_coords = self._get_coords_kwargs(*coords, **kw_coords)

        if var_load is None:
            var_load = slice(None, None, None)

        for coord, key in kw_coords.items():
            if isinstance(key, int):
                kw_coords[coord] = [key]

        # Slice coordinates
        self.coords = self.get_coords_from_backup()
        self._slice_coords(**kw_coords)

        self.vi = self._vi_orr.copy()[var_load]
        self._allocate_memory()

        self._load_data(kw_coords)

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

    def _allocate_memory(self):
        """Allocate data member."""
        self.data = np.zeros(self.shape)

    def _load_data(self, keys):
        # TODO: kwargs
        """Load data.

        Parameters
        ----------
        variables: List[str] or str
            Passed to VariablesInfo.__getitem__
        keys: Dict[coord name, key]
            Passed to Coord.__getitem__
        shape: List[int]
            Shape of data to load excluting number of variables.
        """
        # find the filegroups we need to load
        filegroups = []
        for i, var in self.vi:
            fg = self.filegroups[self.fg_idx[var]]
            try:
                idx = filegroups.index(fg)
            except ValueError:
                filegroups.append([fg, []])
                idx = -1
            filegroups[idx][1].append(var)

        # find the files to load
        # [file, [var], [keys]]
        toload = []
        for fg, varList in filegroups:
            keys_ = {}
            for name, key in keys.items():
                keys_[name] = fg.cs[name].get_slice(key)
            toload += fg.get_commands(varList, keys_)

        for cmd in toload:
            cmd = self._preprocess_load_command(*cmd)
            self._load_cmd(*cmd)

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

        keys_in = self._get_coords_kwargs(**keys_in)
        keys_in = self._sort_by_coords(keys_in)
        keys_slice = self._get_coords_kwargs(**keys_slice)
        keys_slice = self._sort_by_coords(keys_slice)
        return filename, var_list, keys_in, keys_slice

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

    def _post_load(self):
        """Do operations after load."""

    def set_post_load_func(self, func):
        """Set function for post loading treatements.

        Parameters
        ----------
        func: Callable[[]]
        """
        self._post_load = MethodType(func, self)

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


def merge_data(dt1, dt2, varList1=None, varList2=None):
    """Merge two sets of data.

    d1 and d2 are the two Data instances to merge
    varList1 and varList2 are the list of variables to keep in each dataset
    """
    array1, vi1 = dt1.data, dt1.vi
    array2, vi2 = dt2.data, dt2.vi

    # If not variable list are given, all variables are kept
    if not varList1:
        varList1 = vi1.var
    if not varList2:
        varList2 = vi2.var
    varList1 = list(varList1)
    varList2 = list(varList2)

    n = len(varList1) + len(varList2)
    shape = array1.shape[1:]
    assert (array2.shape[1:] == shape), "data should have same shape"

    # Merge Data
    data = np.concatenate((array1[vi1.idx[varList1]],
                           array2[vi2.idx[varList2]]), axis=0)

    # Merge attributes
    fields1 = list(vi1._infos)
    fields2 = list(vi2._infos)

    d = dict(zip(fields1 + fields2,
                 [[None]*n for _ in range(len(fields1+fields2))]))

    for i, var in enumerate(varList1):
        for key in fields1:
            d[key][i] = vi1.__dict__[key][vi1.idx[var]]
    for i, var in enumerate(varList2):
        for key in fields2:
            d[key][len(varList1)+i] = vi2.__dict__[key][vi2.idx[var]]

    kwargs1 = {k: vi1.__dict__[k] for k in vi1._kwargs}
    kwargs2 = {k: vi2.__dict__[k] for k in vi2._kwargs}
    kwargs1.update(kwargs2)

    vi = VariablesInfo(tuple(varList1+varList2), d, **kwargs1)

    return dt1.duplicate_meta(data=data, vi=vi)


def change_variable(data, new_data, old_var, new_var, vi, **kwargs):
    """Change a variable in data."""
    # REVIEW: review

    # Change data
    data[vi.idx[old_var]] = new_data

    # Change var key
    varList = list(vi.var)
    varList[vi.idx[old_var]] = new_var
    vi.var = tuple(varList)

    fields = vi.__dict__.copy()
    for z in ['n', 'var'] + vi._infos:
        fields.pop(z)

    # Use advantage of shallow copy
    for d in fields.values():
        d[new_var] = d.pop(old_var)

    for k, z in kwargs.items():
        vi.__dict__[k][new_var] = z
