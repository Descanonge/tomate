"""Add convenience functions for plotting data."""

import logging
import numpy as np

from mpl_toolkits.axes_grid1 import make_axes_locatable

from data_loader.data_base import DataBase
from data_loader.key import Keyring


log = logging.getLogger(__name__)


class DataPlot(DataBase):
    """Added functionalities for plotting data.

    Attributes
    ----------
    plotted
    plot_coords
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plotted = self.avail.copy()
        self.plotted.empty()

        self.plot_coords = []

    def _make_keyring_none_previous(self, keyring):
        """Replaces None keys by last plotted."""
        for name, key in keyring.items_values():
            if key is None:
                keyring[name] = self.slices_plot[name]

    def set_limits(self, ax, scope=None, *coords, keyring=None, **keys):
        """Set axis limits.

        Parameters
        ----------
        ax: Matplotlib.Axes
        scope: Scope, optional
            Scope to act on. Default is plotted if not empty
            available otherwise.
        coords: str, optional
            Coords to take limit from.
            Default to firts coordinates present in scope,
            of size above 1.
            or first `kw_keys` if present.
        kw_keys: key-like, optional
            Subpart of coordinates to consider.
            If not specified, all coordinates range are taken.
        """
        if scope is None:
            if not self.plotted.is_empty():
                scope = self.plotted
            else:
                scope = self.avail

        if keyring is None:
            keyring = Keyring()
        else:
            keyring = keyring.copy()
        keyring.update(keys)

        if coords:
            names = coords
        elif keyring.kw:
            name = keyring.coords
        else:
            names = scope.get_high_dim()
        keyring.make_full(names)
        keyring.make_total()
        axes = [ax.xaxis, ax.yaxis]
        for i, name in enumerate(names[:2]):
            axis = axes[i]
            limits = scope[name].get_limits(keyring[name].value)
            axis.limit_range_for_scale(*limits)

    def imshow(self, ax, variable, coords=None, limits=True, kwargs=None, **kw_keys):
        """Plot an image on a heatmap.

        Parameters
        ----------
        ax: Matplotlib axis
        variable: str
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
        self._check_loaded()

        keyring = Keyring(**kw_keys)
        keyring.make_full(self.coords_name)
        keyring.make_total()

        if coords is None:
            coords = keyring.get_high_dim()[::-1]
        self.plot_coords = coords

        image = self.view_ordered(coords[::-1], variable, keyring)
        if image.ndim != 2:
            raise IndexError("Selected data does not have the dimension"
                             " of an image %s" % list(image.shape))

        self.plotted = self.get_subscope(variable, keyring, 'loaded')

        kwargs_def = {'origin': 'lower'}
        if kwargs is not None:
            kwargs_def.update(kwargs)
        kwargs = kwargs_def

        extent = self.plotted.get_extent(*coords)
        im = ax.imshow(image, extent=extent, **kwargs)

        if limits:
            self.set_limits(ax, self.plotted, *coords)

        return im

    def update_imshow(self, im, variable=None, **keys):
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
        self.plotted.var = [variable]

        self.plotted = self.get_subscope(variable, scope='loaded', **keys)

        image = self.view_ordered(self.plot_coords[::-1], variable, **keys)
        if image.ndim != 2:
            raise IndexError("Selected data does not have the dimension"
                             " of an image %s" % image.shape)
        im.set_data(image)

    def contour(self, ax, variable, coords=None, limits=True, kwargs=None, **kw_coords):
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
        kw_coords = self.get_coords_full(**kw_coords)
        kw_coords = self.get_coords_none_total(**kw_coords)

        self.set_plot_keys(variable, **kw_coords)
        image = self.view(variable, **kw_coords)

        if image.ndim != 2:
            raise IndexError("Selected data does not have the dimension"
                             " of an image %s" % image.shape)

        if coords is None:
            coords = self.guess_image_coords(kw_coords)[::-1]
        values = [self.coords[name][kw_coords[name]]
                  for name in coords]

        c = ax.contour(*values, image, **kwargs)
        if limits:
            self.set_limits(ax, **{name: kw_coords[name] for name in coords})

        return c

    def update_contour(self, ax, c, variable=None, coords=None, kwargs=None, **kw_coords):
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
            variable = self.last_plot
        kw_coords = self.get_coords_full(**kw_coords)
        kw_coords = self._get_coords_none_previous(**kw_coords)
        image = self.view(variable, **kw_coords)

        if image.ndim != 2:
            raise IndexError("Selected data does not have the dimension"
                             " of an image %s" % image.shape)

        self.set_plot_keys(variable, **kw_coords)

        if coords is None:
            coords = self.guess_image_coords(kw_coords)[::-1]
        values = [self.coords[name][kw_coords[name]]
                  for name in coords]

        for coll in c.collections:
            ax.collections.remove(coll)
        c = ax.contour(*values, image, **kwargs)

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

            divider = make_axes_locatable(ax)
            cax = divider.append_axes("right", "2%", 0)
            label = dt.vi.get_attr_safe('units', var, default='')

            ax.get_figure().colorbar(im, cax=cax, label=label)

            return im

        images = self.iter_axes(axes, plot, variables,
                                limits=limits, kwargs=kwargs, coords=coords,
                                **kw_coords)
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
        def update(ax, dt, var, im, **kw_coords):
            dt.update_imshow(im, var, **kw_coords)
        self.iter_axes(axes, update, variables, iterables=[images], **kw_coords)

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
            variables = self.vi.var
        variables = list(variables)
        for i in range(axes.size - len(variables)):
            variables.append(None)
        for i, var in enumerate(variables):
            if var is None:
                ax = axes.flat[i]
                fig.delaxes(ax)

    def iter_axes(self, axes, func, variables=None, iterables=None, *args, **kwargs):
        """Apply function over multiple axes.

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
            variables = self.vi.var
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
