
.. currentmodule :: data_loader.db_types.plotting

Plotting
========

The plot object
---------------

The package provides various ways to plot your data.
It does so by relying on 'plot objects', from the
:mod:`data_loader.db_types.plotting` module, and matplotlib.
Plot objects are custom objects containing information on what data is plotted
and how it is plotted, and ways to modify the plot once created.
Each type of plot is represented by a subclass of
:class:`plot_object.PlotObjectABC`.
To easily create those objects, one can use the additional methods provided by
:class:`DataPlot<data_plot.DataPlot>`.

.. currentmodule :: data_loader.db_types.plotting.plot_object.PlotObjectABC

The plot object contains a database object, and a scope corresponding to the
plotted data.
To fetch data from the database, the scope should be a child of its loaded scope.
The keyring used for selecting the data to plot (:attr:`keyring` attribute,
which points to `scope.parent_keyring`) should yield data with the
correct dimensions. An exception will only be raised if using class method
:func:`create` to create the plot object.
The scope scan be sliced, or redefined with methods:

* :func:`reset_scope`, that will redefine all keys from the parent
  scope.
* :func:`up_scope`, that will only redefine the keys specified in arguments.

The plot is created by :func:`create_plot`.
The artist can be removed from the axis by :func:`remove` (the figure
might need redrawing).
It can be updated with :func:`update_plot`,
where keys can be specified to update the scope with `up_scope`.

The object retains the axis it was drawn upon under the :attr:`ax` attribute.
And whatever artist was returned by matplotlib in the
:attr:`object` attribute. It can be accessed as a property under
clearer names depending on the plot object (`contour` for contours for instance).


Example
-------

Let's plot a heatmap of the sea surface temperature::

  >>> import matplotlib.pyplot as plt
  >>> fig, ax = plt.subplots()
  >>> im = db.imshow(ax, 'SST', kwargs={'cmap': 'inferno'}, time=0)

I am stupid, I actually wanted to plot another date::

  >>> im.update_plot(time=2)

The user does not need to be stupid to find use in `update_plot`,
it proves very useful when plotting many images::

  >>> for i, d in enumerate(db.loaded.time.index2date()):
  ...     im.update_plot(time=i)
  ...     fig.savefig('{}.png'.format(d.strftime('%F')))

Now, I was stupid again, I did not plot the correct region::

  >>> im.scope.slice_by_value(lat=slice(30, 40))
  >>> im.update_plot()
  >>> im.set_limits()
