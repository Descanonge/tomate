"""Data class.

Encapsulate data in a single numpy array, and metadata,
such as coordinates, units, ...

Data can be loaded onto ram using self.load_data.
Only a subset of data can be loaded.

Each implementation of the class can be tailored to a
a different data arrangement.
Here files are stored in netCDF files. One file per
time step. Data depends on (time, lat, lon) in this order.
Files containing the same variable are kept in the same
directory.
"""


import numpy as np
import netCDF4 as nc

import myPack.analysis as mpa

from .variablesInfo import VariablesInfo


class Data():
    """Encapsulate data array and info about the variables.

    dwd: main directory
    files: Files instance holding files location
    time: Time instance
    lat, lon: array
    get_vi: function to construct vi
    """

    def __init__(self, dwd, files, time, lat, lon, get_vi):
        self.dwd = dwd
        self.files = files

        self.time = time
        self.lat = lat
        self.lon = lon
        self.extent = list(lon[[0, -1]]) + list(lat[[0, -1]])
        self.keys = [slice(None, None) for _ in range(3)]

        self.get_vi = get_vi
        self.vi = get_vi()

    def load_data(self, keys=None, keys_var=None):
        """Load key from all variables into ram.

        varKey select variables to load
        keys is a list of numpy indexables that select what data to load.
        Data is expected to be (time, (depth), latitude, longitude)
        """

        keys, keys_var, shape = self._find_shape(keys, keys_var)
        self._load_data(keys, keys_var, shape)

    def _find_shape(self, keys, keys_var):
        """Find the shape/size of the data to load."""

        if keys is None:
            keys = []

        if keys_var is None:
            keys_var = slice(None, None, None)

        for i in range(len(keys)):
            if isinstance(keys[i], int):
                keys[i] = [keys[i]]
        for i in range(3-len(keys)):
            keys.append(slice(None, None, None))

        # Compute size of asked data
        shape = [0, 0, 0]
        shape_data = [len(self.time), self.lat.size, self.lon.size]
        for i, key in enumerate(keys):
            if isinstance(key, list):
                shape[i] = len(key)
            if isinstance(key, slice):
                shape[i] = len(range(*key.indices(shape_data[i])))

        return keys, keys_var, shape

    def _load_slice_single_var(self, dt, keys, ncname):
        """Load a slice for a single variable."""
        keys_ = keys.copy()
        return dt[ncname][keys_[1:]]

    def _load_data(self, keys, keys_var, shape):
        """Actually load data."""
        vi = self.get_vi()[keys_var]

        # Allocate memory
        data = np.ma.zeros([vi.n, ] + shape)
        data.mask = np.zeros(data.shape, bool)

        # Find groups of files to load
        for vg in self.files.varGroups:
            toload = [var for var in vg.variables if var in vi.var]
            if len(toload) > 0:
                files = np.array(vg.files)[keys[0]]
                for i_time, file in enumerate(files):
                    with nc.Dataset(file, 'r') as dt:
                        for var in toload:
                            D = self._load_slice_single_var(dt, keys,
                                                            vi.ncname[var])

                            i_var = vi.idx[var]
                            data[i_var, i_time] = D

                            # Make sure it is correctly masked
                            try:
                                dt[vi.ncname[var]]._FillValue
                            except AttributeError:
                                data.mask[i_var, i_time] = ~np.isfinite(
                                    data[i_var, i_time].data)

        self.data = data
        self.vi = vi
        self.keys = keys

    def mask_nan(self, missing=True, inland=True, coast=5, chla=True):
        """Replace sst and chla-OC5 fill values by nan.

        Data is already an array.
        Mask in-land and coasts.
        Clip chla values above 3mg.m-3
        coast: number of neighbors to remove
        """
        if missing:
            m = ~np.isfinite(self.data)
            self.data.mask |= m

        if inland:
            m = self.get_land_mask()
            if coast > 0:
                m = mpa.enlarge_mask(m, coast)
            self.data.mask |= m

        if chla:
            A = self.data[self.vi.idx['Chla_OC5']]
            A = np.clip(A, 0, 3)
            self.data[self.vi.idx['Chla_OC5']] = A
            # A[A > 3] = np.nan

    def compute_land_mask(self):
        """Compute land mask and save to disk."""
        compute_land_mask(self.dwd, self.lat, self.lon)

    def get_land_mask(self, keys=None):
        """Return land mask."""
        if keys is None:
            keys = self.keys[-2:]
        mask = np.load(self.dwd + 'land_mask.npy',
                       mmap_mode='r')[tuple(keys)]
        return mask

    def add_variable(self, var, new_data, **kwargs):
        """Concatenante new_data to data, and add kwargs to vi."""
        if self.data is not None:
            self.data = np.ma.concatenate((self.data, new_data), axis=0)
        else:
            self.data = new_data

        self.vi.add_variable(var, **kwargs)

    def pop_variables(self, variables):
        """Remove variables from data and vi."""
        if not isinstance(variables, list):
            variables = [variables]
        keys = self.vi.idx[variables]
        if self.data is not None:
            self.data = np.delete(self.data, [keys], axis=0)
        self.vi.pop_variables(variables)
        # self.vi = self.vi[[k for k in self.vi.var
        #                    if k not in variables]]

    def duplicate_meta(self, **kwargs):
        """Return Data new reference.

        Data is not copied
        kwargs are differing attributes
        """
        new = Data(self.dwd, self.files, self.time, self.lat, self.lon,
                   self.get_vi)
        d = self.__dict__.copy()
        [d.pop(k, None) for k in ['data']]
        new.__dict__.update(d)
        new.__dict__.update(kwargs)
        return new


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

    print(d)
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
    [fields.pop(z) for z in ['n', 'var'] + vi._infos]

    # Use advantage of shallow copy
    for d in fields.values():
        d[new_var] = d.pop(old_var)

    for k, z in kwargs.items():
        vi.__dict__[k][new_var] = z


def compute_land_mask(wd, lat, lon):
    """Compute land mask.

    According to Cartopy (from naturalearthdata.com)
    for a regular grid save it in wd
    """
    from shapely.ops import unary_union
    from cartopy.feature import LAND
    from shapely.geometry.polygon import Polygon

    # Extent
    d = (lon[-1]-lon[0])/10.
    lon_min = np.min(lon) - d
    lon_max = np.max(lon) + d
    lat_min = np.min(lat) - d
    lat_max = np.max(lat) + d
    extent = [(lon_min, lat_min), (lon_max, lat_min),
              (lon_max, lat_max), (lon_min, lat_max)]

    P = Polygon(extent)
    global_land = unary_union(tuple(LAND.geometries()))
    land = global_land.intersection(P)

    mask = mpa.rasterize(land, lon, lat)
    np.save(wd + 'land_mask.npy', mask)
