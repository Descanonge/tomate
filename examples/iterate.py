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


db = get_data()

# One average value per time step.
average = np.zeros(db.avail.time.size)

# We only load a small 2D window
# ranging from 36N to 41N in latitude,
# and from 71W to 62W in longitude.
db.select_by_value(var='SST',
                   lat=slice(36, 41),
                   lon=slice(-71, -62))

# The size slice. Beware, this does not necessarily
# divide roundly the total number of time steps,
# the last slice can be smaller than this.
size_slice = 12

for slice_time in db.avail.iter_slices('time', size=size_slice):
    db.load_selected(time=slice_time)
    avg = db.mean(['lat', 'lon'])
    average[slice_time] = avg


# We could go further and do the computation on only a subpart of
# all available time steps (let's do the first 50 indices).
db.select_by_value(var='SST', lat=slice(36, 41), lon=slice(-71, -62))
for slice_time in db.avail.iter_slice('time', size=size_slice, time=slice(0, 50)):
    db.load_selected(time=slice_time)


# or not iterate through available scope, but selected.
# HOWEVER loading functions all operate on the available scope, and `selected.iter_slice`
# would return a slice for the selected scope.
# Hopefully, selected is a child scope of available, so we can make this work
# by using `iter_slice_parent`.
db.select_by_value(var='SST', lat=slice(36, 41), lon=slice(-71, -62))
db.selected.slice(time=slice(0, 50))
for slice_time in db.selected.iter_slice_parent('time', size=size_slice):
    db.load_selected(time=slice_time)
