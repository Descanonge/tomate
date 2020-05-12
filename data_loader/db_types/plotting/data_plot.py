"""Add convenience functions for plotting data."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK

from typing import List
import logging

import numpy as np
from matplotlib.axes import Axes

from data_loader.custom_types import KeyLikeInt
from data_loader.data_base import DataBase
from data_loader.keys.keyring import Keyring
from data_loader.scope import Scope

from data_loader.db_types.plotting.image import PlotObjectImage


log = logging.getLogger(__name__)


class DataPlot(DataBase):
    """Added functionalities for plotting data."""


        return po

    def imshow(self, ax, variable, data=None, coords=None, plot=True,
               limits=True, kwargs=None, **keys):
        self.check_loaded()
        po = PlotObjectImage.create(self, ax, data=data, coords=coords, kwargs=kwargs,
                                    var=variable, **keys)
        if plot:
            po.create_plot()
        if limits:
            po.set_limits()

        return po

class DataPlot_(DataBase):
    """Added functionalities for plotting data."""

    def imshow(self, ax, variable, data=None, coords=None, limits=True, kwargs=None, **kw_keys):
        """Plot an image on a heatmap.

        Parameters
        ----------
        ax: Matplotlib axis
        variable: str
        data: Array, optional
            Data to use.
        coords: List[str], optional
            Coordinate to plot along.
            If None, selected coordinates with size higher
            than 1 will be used.
        limits: bool, optional
            Set axis limits.
        kwargs: Dict[Any]
            Passed to imshow.
        kw_keys: key-like
            Subset of data to plot.
            Act on available.

        Returns
        -------
        Matplotlib image.

        Raises
        ------
        IndexError:
            If image has wrong shape.
        """
        self.check_loaded()

        keyring = Keyring(var=variable, **kw_keys)
        keyring.make_full(self.dims)
        keyring.make_total()
        keyring.make_var_idx(self.loaded.var)

        if coords is None:
            coords = keyring.get_high_dim()[::-1]
        self.plot_coords = coords

        if data is not None:
            image = data
        else:
            image = self.view_ordered(coords[::-1], keyring)
        if image.ndim != 2:
            raise IndexError("Selected data does not have the dimension"
                             " of an image %s" % list(image.shape))

        self.plotted = self.get_subscope('loaded', keyring)

        kwargs_def = {'origin': 'lower'}
        if kwargs is not None:
            kwargs_def.update(kwargs)
        kwargs = kwargs_def

        extent = self.plotted.get_extent(*coords)
        im = ax.imshow(image, extent=extent, **kwargs)

        if limits:
            self.set_limits(ax, *coords, scope=self.plotted)

        return im

    def update_imshow(self, im, variable=None, data=None, **keys):
        """Update a heatmap plot.

        If a parameter is None, the value used for setting
        the plot is used.

        Parameters
        ----------
        im: Matplotlib image
        variable: str
            If None, last plotted is used.
        kw_keys: Keys
            Subset of data to plot.
            Act on available.
            If missing, last plotted is used.

        Raises
        ------
        IndexError:
            If image has wrong shape.
        """
        if variable is None:
            variable = self.plotted.var[0]
        self.plotted = self.get_subscope('loaded', var=variable, **keys)

        coords = self.plot_coords

        if data is not None:
            image = data
        else:
            image = self.view_ordered(coords[::-1], var=variable, **keys)
        if image.ndim != 2:
            raise IndexError("Selected data does not have the dimension"
                             " of an image %s" % str(image.shape))
        im.set_data(image)

        # TODO: colorbar

    def contour(self, ax, variable, coords=None, limits=True, kwargs=None, **keys):
        """Plot contour of a variable.

        Parameters
        ----------
        ax: Matplotlib axis
        variable: str
        coords: List[str], optional
            Coordinates to plot along to.
            If None, selected coordinates with dimension higher
            than 1 will be used.
        limits: bool, optional
            Set axis limits.
        kwargs: Dict[Any]
            Passed to contour.
        kw_coords: Keys
            Subset of data to plot.

        Returns
        -------
        Matplotlib contour

        Raises
        ------
        IndexError:
            If image has wrong shape.
        """
        self.check_loaded()

        if kwargs is None:
            kwargs = {}

        keyring = Keyring(var=variable, **keys)
        keyring.make_full(self.dims)
        keyring.make_total()
        keyring.make_var_idx(self.loaded.var)

        if coords is None:
            coords = keyring.get_high_dim()[::-1]
        self.plot_coords = coords

        self.plotted = self.get_subscope('loaded', keyring)

        image = self.view_ordered(coords[::-1], keyring)
        if image.ndim != 2:
            raise IndexError("Selected data does not have the dimension"
                             " of an image %s" % image.shape)

        coord_values = [self.plotted[name][:]
                        for name in coords]

        c = ax.contour(*coord_values, image, **kwargs)
        if limits:
            self.set_limits(ax, *coords, scope=self.plotted)

        return c

    def update_contour(self, ax, c, variable=None, coords=None, kwargs=None, **keys):
        """Update a contour plot.

        Parameters
        ----------
        ax: Matplotlib axis
        c: Contour
        variable: str, optional
            If None, previously plotted is used.
        coords: List[str], optional
            Coordinates to use.
            If None, selected coordinates with size higher
            than 1 will be used.
        kwargs: Dict[An]
            Passed to contour.
        kw_coords: Keys
            Subset of data to plot.
            If missing, last plotted is used.

        Raises
        ------
        IndexError:
            If image has wrong shape.
        """
        if variable is None:
            variable = self.plotted.var[0]

        for coll in c.collections:
            ax.collections.remove(coll)

        c = self.contour(ax, variable, coords=coords, limits=False, kwargs=kwargs, **keys)

        return c

    def imshow_all(self, axes, variables=None, coords=None, limits=None, kwargs=None, **kw_coords):
        """Plot all variables.

        Parameters
        ----------
        axes: Array of Matplotlib axis
        variables: List[str]
            List of variable to plot.
            None elements will be skipped, and the
            corresponding axe deleted.
        coords: List[str], optional
            Coordinate to plot along.
            If None, selected coordinates with size higher
            than 1 will be used.
        limits: bool, optional
            Set axis limits.
        kwargs: Dict[Any]
            Passed to imshow.
        kw_coords: Keys
            Subset of data to plot.

        Returns
        -------
        Array of Matplotlib images.
        """
        def plot(ax, dt, var, **kwargs):
            im_kw = {'vmin': dt.vi.get_attr_safe('vmin', var),
                     'vmax': dt.vi.get_attr_safe('vmax', var)}

            if kwargs['kwargs'] is None:
                kwargs['kwargs'] = {}
            im_kw.update(kwargs.pop('kwargs'))

            im = dt.imshow(ax, var, kwargs=im_kw, **kwargs)
            title = dt.vi.get_attr_safe('fullname', var, default=var)
            ax.set_title(title)

            if _has_matplotlib:
                divider = make_axes_locatable(ax)
                cax = divider.append_axes("right", "2%", 0)
                label = dt.vi.get_attr_safe('units', var, default='')
                ax.get_figure().colorbar(im, cax=cax, label=label)

            return im

        if variables is None:
            variables = self.loaded.var[:]
        images = self.iter_axes(axes, plot, variables,
                                limits=limits, kwargs=kwargs, coords=coords,
                                **kw_coords)
        self.plotted = self.get_subscope('loaded', var=variables, **kw_coords)
        return images

    def update_imshow_all(self, axes, images, variables=None, **kw_coords):
        """Update plots of multiple variables.

        Parameters
        ----------
        axes: Array of Matplotlib axes
        images: Array of Matplotlib images
        variables: List[str]
        kw_coords: Keys
        """
        if variables is None:
            variables = self.plotted.var[:]
        def update(ax, dt, var, im, **kw_coords):
            dt.update_imshow(im, var, **kw_coords)
        self.iter_axes(axes, update, variables, iterables=[images], **kw_coords)
        self.plotted = self.get_subscope('loaded', var=variables, **kw_coords)

    def del_axes_none(self, fig, axes, variables=None):
        """Delete axes for which variables is None.

        Parameters
        ----------
        fig: Matplotlib figure
        axes: Array of Matplotlib axes
        variables: List[str]
            List of variables. If element is None,
            axis will be removed from figure.
        """
        if variables is None:
            variables = self.loaded.var[:]
        variables = list(variables)
        for i in range(axes.size - len(variables)):
            variables.append(None)
        for i, var in enumerate(variables):
            if var is None:
                ax = axes.flat[i]
                fig.delaxes(ax)

    def iter_axes(self, axes, func, variables=None, iterables=None, *args, **kwargs):
        r"""Apply function over multiple axes.

        Parameters
        ----------
        axes: Array of Matplotlib axis
            Axes to iterate on.
        func: Callable
            Function to call for every axe.
            func(ax, DataPlot, variable, \*iterable, \*\*kwargs)
        variables: List[str]
            None elements will be skipped.
        iterables: List[List[Any]]
            Argument passed to `func`, changing
            for every axis.
        kwargs: Any
            Passed to func.
        """
        if variables is None:
            variables = self.loaded.var[:]
        if iterables is None:
            iterables = []
        iterables = [np.array(c) for c in iterables]

        output = [None for _ in range(axes.size)]
        for i, var in enumerate(variables):
            ax = axes.flat[i]
            iterable = [c.flat[i] for c in iterables]

            if var is not None:
                output[i] = func(ax, self, var, *iterable, *args, **kwargs)

        output = np.array(output)
        output = np.reshape(output, axes.shape)
        return output

    def hoevmuller(self):
        pass

    # TODO: hoevmuller plot

    def plot_histogram(self, ax, variable, kwargs=None, **keys):
        if kwargs is None:
            kwargs = {}

        kw = {'density': True}
        kw.update(kwargs)
        data = self.view(variable, **keys).compressed()
        ax.hist(data, **kw)
