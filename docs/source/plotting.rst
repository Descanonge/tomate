
.. currentmodule :: tomate.db_types.plotting

Plotting
========

The plot object
---------------

The package provides various ways to plot your data.
It does so by relying on 'plot objects', from the
:mod:`tomate.db_types.plotting` module, and matplotlib.
Plot objects are custom objects containing information on what data is plotted
and how it is plotted, and ways to modify the plot once created.
Each type of plot is represented by a subclass of
:class:`plot_object.PlotObjectABC`.
To easily create those objects, one can use the additional database methods
provided by :class:`DataPlot<data_plot.DataPlot>`.

Note that all those methods do their selection of what part of data to plot
by value. One can still select by index by appending '_idx' to the keyword
argument of a dimension. See examples below.

.. currentmodule :: tomate.db_types.plotting.plot_object.PlotObjectABC

The plot object contains a database object, and a scope corresponding to the
plotted data.
The keyring used for selecting the data to plot (:attr:`keyring` attribute,
which points to `scope.parent_keyring`) should yield data with the
correct dimensions.
The scope scan be sliced, or redefined with the methods:

* :func:`reset_scope`, that will redefine all keys from the parent
  scope.
* :func:`update_scope`, that will only redefine the keys specified in arguments.

The plot is created by :func:`create_plot`.
The artist can be removed from the axis by :func:`remove` (the figure
might need redrawing).
It can be updated with :func:`update_plot`.

The object retains the axis it was drawn upon under the :attr:`ax` attribute.
And whatever artist was returned by matplotlib in the
:attr:`object` attribute. It can be accessed as a property under
clearer names depending on the plot object (`contour` for contours for instance).

The plot object also provides a colobar under the :attr:`cax` attribute. See
:func:`add_colorbar`.
It also can quickly set the plot limits according to the scope using
:func:`set_limits`, and add labels with :func:`set_labels`.


Example
-------

Let's plot a heatmap of the sea surface temperature::

  >>> import matplotlib.pyplot as plt
  >>> fig, ax = plt.subplots()
  >>> im = db.imshow(ax, 'SST', kwargs={'cmap': 'inferno'}, time_idx=0)

Oh no, I am stupid, I actually wanted to plot another date::

  >>> im.update_plot(time=2)

I was stupid again, I did not plot the correct region::

  >>> im.scope.slice_by_value(lat=slice(30., 40.))
  >>> im.update_plot()
  >>> im.set_limits()

Note that the user does not need to be stupid to find use in `update_plot`: it
proves very useful when plotting many images::

  >>> for i, d in enumerate(db.loaded.time.index2date()):
  ...     im.update_plot(time=i)
  ...     fig.savefig('{}.png'.format(d.strftime('%F')))


Funkier example
---------------

Let's look at average plot (*ie* plots where one or more dimensions
were averaged). I am going to plot an Hovmüller diagram of the SST where
the longitude is averaged between 100W and 0E, and
underneath the average SST for the entire area::

  >>> fig, [ax1, ax2] = plt.subplots(2, 1, sharex=True)
  >>> im = db.imshow_avg(ax1, 'SST', avg_dims=['lon'],
  ...                    lon=slice(-100, 0))
  >>> im.ax.set_aspect('auto')
  >>> line = db.plot_avg(ax2, 'SST', avg_dims=['lon', 'lat']
  ...                    lon=slice(-100, 0))
