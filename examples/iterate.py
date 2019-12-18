"""Iterate through the available data.

One goal of this package is to be able to load
only a subset of all the data available.

A frequent use case is the need to apply a
process on all the data available, without being
able to load everything at once because of memory
limitation.
To solve this problem, the database object offers
the possibility to iterate easily through a coordinate,
by slices of a certain size.

This script present this feature by computing the
SST average over a small 2D window, over all time steps
avaible, but by only loading 12 time steps at once.
"""

import numpy as np

from tailored import get_data


dt = get_data(["SST"])

# One average value per time step.
average = np.zeros(dt['time'].size)

# We only load a small 2D window
# ranging from 36N to 41N in latitude,
# and from 71W to 62W in longitude.
slice_lat = dt['lat'].subset(36, 41)
slice_lon = dt['lon'].subset(-71, -62)

# The size slice. Beware, this does not necessarily
# divide roundly the total number of time steps,
# the last slice can be smaller than this.
size_slice = 12

for slice_time in dt.iter_slices('time', size_slice=size_slice):
    dt.load_data('SST', time=slice_time, lat=slice_lat, lon=slice_lon)

    avg = np.nanmean(dt['SST'], axis=[1, 2])
    average[slice_time] = avg
