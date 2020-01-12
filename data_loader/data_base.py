"""Base class for data."""

import logging
from types import MethodType

import numpy as np

from data_loader.coord import Coord
from data_loader.iter_dict import IterDict
from data_loader.time import Time


log = logging.getLogger(__name__)


class DataBase():
    """Encapsulate data array and info about the variables.

    Data and coordinates can be accessed with getter:
    Data[{name of variable | name of coordinate}]

    Data is loaded from disk with load_data.

    Parameters
    ----------
    root: str
        Root data directory containing all files.
    filegroups: List[Filegroups].
    vi: VariablesInfo
        Information on the variables.
    coords: List[Coord]
        Coordinates.

    Attributes
    ----------
    data: Numpy array
        Data array if loaded.
    filegroups: List[Filegroup]
    _fg_idx: Dict[variable: str, int]
        Index of filegroup for each variable

    vi: VariablesInfo
    _vi_bak: VariablesInfo
        Copy of the vi at its initial state.

    coords_name: List[str]
        Coordinates names, in the order the data
        is kept.
    coords: Dict[str, Coord]
        Coordinates by name, in the order the data
        is kept.
    _coords_bak: Dict[str, Coord]
        Copies of the coordinates it their initial
        state.
    slices: Dict
        Selected (and eventually loaded) part of
        each coordinate.
    """

    def __init__(self, root, filegroups, vi, *coords):
        self.root = root

        names = [c.name for c in coords]
        coords_bak = IterDict(dict(zip(names, coords)))
        self.coords_name = names
        self._coords_bak = coords_bak
        self.coords = self.get_coords_from_backup()
        self.slices = {c.name: slice(0, c.size, 1) for c in coords}

        self._fg_idx = {}
        self.filegroups = filegroups
        for i, fg in enumerate(filegroups):
            for var in fg.contains:
                self._fg_idx.update({var: i})

        self.vi = vi
        self._vi_bak = vi.copy()

        self.data = None

        self.link_filegroups()

    def __str__(self):
        s = ["Data object"]

        s1 = "Class: %s, Bases: " % self.__class__.__name__
        s2 = ', '.join(self.bases.values())
        s.append(s1 + s2)
        s.append('')

        s.append("Variables: %s" % ', '.join(self.vi.var))
        s.append('')

        s.append("Data selected:")
        s += ["\t%s: %s (%s)" % (c.name, c.get_extent_str(), c.size)
              for c in self.coords.values()]
        s.append('')

        s.append("Data available:")
        s += ["\t%s: %s (%d)" % (c.name, c.get_extent_str(), c.size)
              for c in self.get_coords_from_backup().values()]
        s.append('')

        if self.data is None:
            s.append('Data not loaded')
        else:
            s.append('Data loaded: %s' % str(self.slices))
        s.append('')

        s.append("%d Filegroups:" % len(self.filegroups))
        s += ['\t%s' % ', '.join(fg.contains) for fg in self.filegroups]

        return '\n'.join(s)

    @property
    def bases(self):
        """Return dictionary of base classes names.

        Returns
        -------
        bases: Dict
            {class name: full name with module}
        """
        bases = self.__class__.__bases__
        out = {c.__name__: '%s.%s' % (c.__module__, c.__name__)
               for c in bases}
        return out

    def _check_loaded(self):
        if self.data is None:
            raise RuntimeError("Data not loaded.")

    def __getitem__(self, y):
        """Return a coordinate, or data for a variable.

        If y is a coordinate name, return the coordinate.
        If y is a variable name, return the corresponding data slice.
        Else, it is transmitted to data.__getitem__().

        Parameters
        ----------
        y: str, or anything for a numpy array.

        Raises
        ------
        KeyError
            If key is string and not a coordinate or variable.
        """
        if isinstance(y, str):
            if y in self.vi.var:
                y = self.vi.idx[y]
            elif y in self.coords_name:
                return self.coords[y]
            else:
                raise KeyError("Key '%s' not in coordinates or variables" % y)

        return self.data[y]

    def __getattribute__(self, item):
        """Get attribute.

        Can be used to retrieve coordinate by name.
        """
        if item in super().__getattribute__('coords_name'):
            return super().__getattribute__('coords')[item]
        return super().__getattribute__(item)

    def _select(self, variables, kw_coords):
        """Returns a subset of data.

        No processing of arguments.
        kw_coords must be full, sorted.

        Parameters
        ----------
        variables: List[str]
        kw_coords: Dict[keys]
        """
        idx = self.vi.idx[variables]
        keys = tuple(idx + list(kw_coords.values()))
        return self.data[keys]

    def select(self, variables=None, **kw_coords):
        """Returns a subset of data.

        Parameters
        ----------
        variables: str or List[str]
            If None, all variables are taken.
        kw_coords: Int or List[int] or slice
            If None, total is taken.
        """
        if variables is None:
            variables = self.vi.var
        elif isinstance(variables, str):
            variables = [variables]

        kw_coords = self.get_coords_full(**kw_coords)
        kw_coords = self.get_coords_none_total(**kw_coords)
        kw_coords = self.sort_by_coords(kw_coords)
        return self._select(variables, kw_coords)

    def iter_slices(self, coord, size_slice=12):
        """Iter through data with slices of `coord` of size `n_iter`.

        Parameters
        ----------
        coord: str
            Coordinate to iterate along to.
        size_slice: int, optional
            Size of the slices to take.
        """
        # TODO: Add subset selection
        c = self.get_coords_from_backup(coord)[coord]

        n_slices = int(np.ceil(c.size / size_slice))
        slices = []
        for i in range(n_slices):
            start = i*size_slice
            stop = min((i+1)*size_slice, c.size)
            slices.append(slice(start, stop))

        return slices

    def iter_slices_month(self, coord='time'):
        """Iter through data with slices corresponding to a month.

        Parameters
        ----------
        coord: str, optional
            Coordinate to iterate along to.
            Must be subclass of Time.

        Raises
        ------
        TypeError:
            If the coordinate is not a subclass of Time.

        See also
        --------
        iter_slices: Iter through any coordinate
        """
        c = self.get_coords_from_backup(coord)[coord]
        if not issubclass(type(c), Time):
            raise TypeError("'%s' is not a subclass of Time (is %s)"
                            % (coord, type(coord)))

        dates = c.index2date()
        slices = []
        indices = []
        m_old = dates[0].month
        y_old = dates[0].year
        for i, d in enumerate(dates):
            m = d.month
            y = d.year
            if m != m_old or y != y_old:
                slices.append(indices)
                indices = []
            indices.append(i)
            m_old = m
            y_old = y

        return slices

    def link_filegroups(self):
        """Link filegroups and data."""
        for fg in self.filegroups:
            fg.db = self

    @property
    def dim(self):
        """Number of dimensions."""
        return len(self.coords_name)

    @property
    def shape(self):
        """Shape of the data from how coordinates and variables are selected.

        Returns
        -------
        List[int]
        """
        return [self.vi.n] + [c.size for c in self.coords.values()]

    def get_coords_from_backup(self, *coords):
        """Remake coordinates from backup.

        Parameters
        ----------
        coords: List[str]
            Coord to select. If None, all coordinates
            are taken.

        Returns
        -------
        IterDict[Coord]
        """
        if not coords:
            coords = self.coords_name
        coords_bak = [self._coords_bak[name] for name in coords]
        copy = [c.copy() for c in coords_bak]
        coords = IterDict(dict(zip(coords, copy)))
        return coords

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

    def get_limits(self, *coords, **kw_coords):
        """Return limits of coordinates.

        Min and max values for specified coordinates.

        Parameters
        ----------
        coords: List[str]
            Coordinates name.
            If None, defaults to all coordinates, in the order
            of data.
        kw_coords: Any
            Subset of coordinates

        Returns
        -------
        limits: List[float]
            Min and max of each coordinate. Flattened.

        Examples
        --------
        >>> print(dt.get_limits('lon', 'lat'))
        [-20.0 55.0 10.0 60.0]

        >>> print(dt.get_extent(lon=slice(0, 10)))
        [-20.0 0.]
        """
        if not coords:
            coords = self.coords_name
        kw_coords.update({name: None for name in coords})

        limits = []
        for name, key in coords:
            limits += self[name].get_limits(key)
        return limits

    def get_extent(self, *coords, **kw_coords):
        """Return extent of coordinates.

        Return first and last value of specified coordinates.

        Parameters
        ----------
        coords: List[str]
            Coordinates name.
            If None, defaults to all coordinates, in the order
            of data.
        kw_coords: Any
            Subset of coordinates

        Returns
        -------
        limits: List[float]
            First and last values of each coordinate.

        Examples
        --------
        >>> print(dt.get_extent('lon', 'lat'))
        [-20.0 55.0 60.0 10.0]

        >>> print(dt.get_extent(lon=slice(0, 10)))
        [-20.0 0.]
        """
        if not coords:
            coords = self.coords_name
        kw_coords.update({name: None for name in coords})
        kw_coords = self.get_coords_none_full(**kw_coords)

        extent = []
        for name, key in kw_coords.items():
            extent += self[name].get_extent(key)
        return extent

    def get_coords_kwargs(self, *coords, **kw_coords):
        """Make standard, full kwargs when asking for coordinates parts.

        From a mix of positional and keyword argument,
        make a list of keywords, containing all coords.
        Keywords arguments take precedence over positional arguments.

        Parameters
        ----------
        coords: Slice, int, or List[int]
            Key for subsetting coordinates, order is that
            of self.coords.
        kw_coords: Slice, int or List[int]
            Key for subsetting coordinates.

        Exemples
        --------
        >>> print( dt.get_loords_kwargs([0, 1], lat=slice(0, 10)) )
        {'time': [0, 1], 'lat': slice(0, 10), 'lon': slice(None, None)}
        """

        if not coords:
            coords = []

        if not kw_coords:
            kw_coords = {}

        for i, key in enumerate(coords):
            name = self.coords_name[i]
            if name not in kw_coords:
                kw_coords[name] = key

        return kw_coords

    def get_coords_full(self, **kw_coords):
        """Add missing coords in dictionnary."""
        for coord in self.coords_name:
            if coord not in kw_coords:
                kw_coords[coord] = None
        return kw_coords

    @staticmethod
    def get_coords_none_total(**kw_coords):
        """Replaces None keys by total slices."""
        for name, key in kw_coords.items():
            if key is None:
                kw_coords[name] = slice(None, None)
        return kw_coords

    def sort_by_coords(self, dic):
        """Sort dictionnary.

        The order is that of `self.coords_name`.
        """
        # Make sure keys are coords name
        keys = {}
        for key, value in dic.items():
            c = self.get_coord(key)
            keys[c.name] = [key, value]

        # Order dictionary
        keys_ord = {}
        for name in self.coords_name:
            key, value = keys[name]
            keys_ord[key] = value

        return keys_ord

    def set_slice(self, variables=None, **kw_coords):
        """Pre-select variables and coordinates slices.

        Selection is applied to **available** coordinates.
        Should be used only if data is not loaded,
        otherwise use `slice_data`.

        This selection is reset when using self.load_data.

        Parameters
        ----------
        variables: List[str], optional
            Variables to select, from all those available.
            If None, all available are selected.
        kw_coords: int, Slice, or List[int]
            Part of coordinates to select, from the full
            available extent.
            If None, everything available is selected.

        See also
        --------
        slice_data: For when data is loaded.
        """
        if self.data is not None:
            log.warning("Using set_coords_slice with data loaded can decouple "
                        "data and coords. Use slice_data instead.")

        if variables is None:
            variables = slice(None, None)

        kw_coords = self.get_coords_full(**kw_coords)
        kw_coords = self.get_coords_none_total(**kw_coords)
        kw_coords = self.sort_by_coords(kw_coords)

        for name, key in kw_coords.items():
            reject = not isinstance(key, (int, slice))
            if isinstance(key, (list, tuple)):
                reject = not all(isinstance(z, int) for z in key)
            elif isinstance(key, int):
                kw_coords[name] = [key]
            if reject:
                raise ValueError("'%s' key is not an integer, list of integers, or slice"
                                 " (is %s)" % (name, type(key)))

        self.vi = self._vi_bak[variables]

        coords = self.get_coords_from_backup()
        for name, key in kw_coords.items():
            coords[name].slice(key)
            self.slices[name] = key
        self.coords = coords

    def slice_data(self, variables=None, **kw_coords):
        """Select a subset of loaded data and coords.

        Selection is applied to **loaded** coordinates and variables.
        If data is loaded, the array is also sliced.

        Parameters
        ----------
        variables: str or List[str], optional
            Variables to select, from those already selected or loaded.
            If None, no change are made.
        kw_coords: int, Slice, or List[int]
            Part of coordinates to select, from part already selected or loaded.
            If None, no change are made.
        """
        if variables is None:
            variables = self.vi.var
        kw_coords = self.get_coords_full(**kw_coords)
        kw_coords = self.get_coords_none_total(**kw_coords)
        kw_coords = self.sort_by_coords(kw_coords)

        for name, key in kw_coords.items():
            self.coords[name].slice(key)
            self.slices[name] = subset_slices(self.slices[name], key)

        if self.data is not None:
            self.data = self._select(variables, kw_coords)

    def unload_data(self):
        """Remove data, return coordinates and variables to all available."""
        self.data = None
        self.set_slice()

    def load_data(self, variables, *coords, **kw_coords):
        """Load part of data from disk into memory.

        What variables, and what part of the data
        corresponding to coordinates indices can be specified.

        Parameters
        ----------
        variables: str or List[str]
            Variables to load. If None, all variables available
            are taken.
        coords: int, Slice, or List[int]
            What subset of coordinate to load. The order is that
            of self.coords.
            If None, all available is taken.
        kw_coords: int, Slice, or List[int]
            What subset of coordinate to load. Takes precedence
            over positional `coords`.
            If None, all availabce is taken.

        Examples
        --------
        Load everything available

        >>> dt.load_data(None)

        Load first index of the first coordinate for the SST variable

        >>> dt.load_data("SST", 0)

        Load everything for SST and Chla variables.

        >>> dt.load_data(["SST", "Chla"], slice(None, None), None)

        Load time steps 0, 10, and 12 of all variables.

        >>> dt.load_data(None, time=[0, 10, 12])

        Load first index of the first coordinate, and a slice of lat
        for the SST variable.

        >>> dt.load_data("SST", 0, lat=slice(200, 400))
        """
        self.unload_data()
        kw_coords = self.get_coords_kwargs(*coords, **kw_coords)
        self.set_slice(variables=variables, **kw_coords)
        self.data = self.allocate_memory(self.shape)

        fg_var = self._get_filegroups_for_variables(self.vi.var)
        for fg, var_load in fg_var:
            fg.load_data(var_load, self.slices)

        try:
            self.do_post_load() #pylint: disable=not-callable
        except NotImplementedError:
            pass

    @staticmethod
    def allocate_memory(shape):
        """Allocate data array.

        Parameters
        ----------
        shape: List[int]
            Shape of the array to allocate.

        Returns
        -------
        Array
        """
        log.info("Allocating numpy array of shape %s", shape)
        return np.zeros(shape)

    @property
    def _concatenate(self):
        """Concatenate function."""
        return np.concatenate

    def _get_filegroups_for_variables(self, variables):
        """Find the filegroups corresponding to variables.

        Parameters
        ----------
        variables: List[str]

        Returns
        -------
        fg_var: List[List[Filegroup, List[str]]
            A list of the filegroups with the corresponding variables.
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

    def set_post_load_func(self, func):
        """Set function for post loading treatements.

        Parameters
        ----------
        func: Callable[[DataBase or subclass]]
            Function to execute after data is loaded.
            See do_post_load() for a better description
            of the function interface.

        """
        self.do_post_load = MethodType(func, self)

    def do_post_load(self): #pylint: disable=method-hidden
        """Do post loading treatments.

        Raises
        ------
        NotImplementedError
            If do_post_load was not set.
        """
        raise NotImplementedError("do_post_load was not set.")

    def set_data(self, var, data):
        """Set the data for a single variable.

        Parameters
        ----------
        var: str
            Variable to set the data to.
        data: Array
            Array of the correct shape for currently
            selected coordinates. Has no axis for variables.

        Raises
        ------
        IndexError
            If the data has not the right dimension.
        ValueError
            If the data is not of the shape of current selection.

        Examples
        --------
        """
        if data.ndim != self.dim:
            raise IndexError("data of wrong dimension (%s, expected %s)" %
                             (data.ndim, self.dim))

        if list(data.shape) != self.shape[1:]:
            raise ValueError("data of wrong shape (%s, expected %s)" %
                             (list(data.shape), self.shape[1:]))

        data = np.expand_dims(data, 0)

        # No data is loaded
        if self.data is None:
            self.data = data

        # Variable is already loaded
        elif var in self.vi.var:
            self[var][:] = data[0]

        # Variable is not loaded, others are
        else:
            self.vi = self._vi_bak[self.vi.var + [var]]
            self.data = self._concatenate((self.data, data), axis=0)

    def add_variable(self, variable, data, **infos):
        """Concatenante new_data to data, and add kwargs to vi.

        Parameters
        ----------
        variable: str
            Variable to add
        data: Array
            Corresponding data
        infos:
            Passed to VariablesInfo.add_variable
        """
        self.vi.add_variable(variable, **infos)
        if self.data is not None:
            null = self.allocate_memory([1] + self.shape[1:])
            self.data = self._concatenate((self.data, null), 0)
        self.set_data(variable, data)

    def pop_variables(self, variables):
        """Remove variables from data and vi.

        Parameters
        ----------
        variables: List[str]
            Variables to remove.
        """
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
        variables: str or List[str]
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
    """Compound slices and lists when subsetting a coord.

    Parameters
    ----------
    key: Slice or List[int]
        Current slice of a coordinate.
    key_subset: Slice or List[int]
        Asked slice of coordinate.
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
