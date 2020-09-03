"""Some examples of simple plots."""

import matplotlib.pyplot as plt

from tailored import get_data

db = get_data()


## A simple heatmap of the sea surface temperature

db.load(time=0)

fig, ax = plt.subplots()

im = db.imshow(ax, 'SST', time_idx=0)

im.add_colorbar()
im.set_labels()


## We loop over time to create multiple images

db.load(time=slice(0, 10))

fig, ax = plt.subplots()

im = db.imshow(ax, 'SST', time_idx=0)
im.add_colorbar()
im.set_labels()

for i, d in enumerate(db.loaded.time.index2date()):
    im.update_plot(time=i)
    fig.savefig('{}.png'.format(d.strftime('%F')), dpi=150)


## The time evolution of a single position

db.load(time=slice(0, 10))

fig, ax = plt.subplots()

line = db.plot(ax, 'SST', lon=-70., lat=40.)

line.set_labels()


## An Hovmüller and the evolution of the average temperature
# Note our data is order as [time, lat, lon]. So after averaging
# we have data as [time, lat]. Matplotlib imshow will naturally
# put time in X-axis and lat Y-axis. This is fine for this plot,
# so I don't specify anything about the axes. See next plot
# for another situation.
#
# The averaging will be done between 80W and 0E.

db.load_by_value(time=slice((2007, 1, 1), (2007, 12, 31)))

fig, [ax1, ax2] = plt.subplots(2, 1, sharex=True)

im = db.imshow_avg(ax1, 'SST', avg_dims=['lon'], lon=slice(-80, 0))
im.ax.set_aspect('auto')
im.add_colorbar()

line = db.plot_avg(ax2, 'SST', avg_dims=['lon'], lon=slice(-80, 0))
line.set_labels()


## A vertical cut in the water temperature
# Let's pretend our data now has a 'depth' dimension.
# Our cut will be along a meridian.
# Our X-axis will be latitude, and Y-axis will be depth

db.load(time=0)

fig, ax = plt.subplots()

im = db.imshow(ax, 'theta', time_idx=0, lon=-30, axes=['lat', 'depth'])
im.add_colorbar()
im.set_labels()
