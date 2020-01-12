"""Add convenience functions for plotting data."""

import logging
import numpy as np

from mpl_toolkits.axes_grid1 import make_axes_locatable

from data_loader.data_base import DataBase


log = logging.getLogger(__name__)


class DataPlot(DataBase):
    """Added functionalities for plotting data.

    Attributes
    ----------
    variables_plot: List[str]
    slices_plot: Dict
        What part of the data have been plotted.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.last_plot = ''
        self.slices_plot = {}
        for name, key in self.slices.items():
            try:
                k = key.copy()
            except AttributeError:
                k = key
            self.slices_plot[name] = k

    def _get_coords_none_previous(self, **kw_coords):
        """Replaces None keys by last plotted."""
        for name, key in kw_coords.items():
            if key is None:
                kw_coords[name] = self.slices_plot[name]
        return kw_coords

    @staticmethod
    def _get_coords_none_single(idx=0, **kw_coords):
        """Replaces None keys by index."""
        for name, key in kw_coords.items():
            if key is None:
                kw_coords[name] = idx
        return kw_coords

    def set_plot_keys(self, variable=None, **kw_coords):
        """Set last plotted data."""
        if variable is not None:
            self.last_plot = variable

        for name, key in kw_coords.items():
            self.slices_plot[name] = key

    def set_limits(self, ax, *coords, **kw_coords):
        """Set axis limits."""
        if len(coords) + len(kw_coords) > 2:
            log.warning('Only first two arguments will be used.')

        keys = {}
        for i, key in enumerate(coords[:2]):
            keys[['lon', 'lat'][i]] = key

        for name, key in kw_coords.items():
            if len(keys) > 2:
                break
            keys[name] = key

        for i in range(len(keys), 2):
            if 'lon' not in keys:
                keys['lon'] = None
            if 'lat' not in keys:
                keys['lat'] = None

        kw_coords = self.get_coords_none_total(**keys)
        names = list(kw_coords.keys())
        ax.set_xlim(*self.coords[names[0]].get_limits(kw_coords[names[0]]))
        ax.set_ylim(*self.coords[names[1]].get_limits(kw_coords[names[1]]))

    def imshow(self, ax, variable, coords=None, limits=True, kwargs=None, **kw_coords):
        """Plot a frame on a heatmap.

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
        kw_coords: Keys
            Subset of data to plot.

        Returns
        -------
        Matplotlib image.
        """
        self._check_loaded()

        kw_coords = self.get_coords_full(**kw_coords)
        if coords is not None:
            keys_hor = self.get_coords_none_total(**{k: kw_coords[k]
                                                     for k in coords})
            kw_coords.update(keys_hor)
        kw_coords = self._get_coords_none_single(**kw_coords)

        frame = self.select(variable, **kw_coords)
        self.set_plot_keys(variable, **kw_coords)

        kwargs_def = {'origin': 'lower'}
        if kwargs is not None:
            kwargs_def.update(kwargs)
        kwargs = kwargs_def

        if coords is None:
            coords = self.guess_map_coords(kw_coords)
        slices = [kw_coords[name] for name in coords]
        extent = self.get_extent(dict(zip(coords, slices)))

        im = ax.imshow(frame, extent=extent, **kwargs)

        if limits:
            self.set_limits(ax, slices)

        return im

    def update_imshow(self, im, variable=None, **kw_coords):
        """Update a heatmap plot.

        If a parameter is None, the value used for setting
        the plot is used.

        Parameters
        ----------
        im: Matplotlib image
        variable: str
            If None, last plotted is used.
        kw_coords: Keys
            Subset of data to plot.
            If missing, last plotted is used.
        """
        if variable is None:
            variable = self.last_plot
        kw_coords = self.get_coords_full(**kw_coords)
        kw_coords = self._get_coords_none_previous(**kw_coords)
        self.set_plot_keys(variable, **kw_coords)

        frame = self.select(variable, **kw_coords)
        im.set_data(frame)

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
        """
        kw_coords = self.get_coords_full(**kw_coords)
        if coords is not None:
            keys_hor = self.get_coords_none_total(**{k: kw_coords[k]
                                                     for k in coords})
            kw_coords.update(keys_hor)
        kw_coords = self._get_coords_none_single(**kw_coords)

        self.set_plot_keys(variable, **kw_coords)
        frame = self.select(variable, **kw_coords)

        if coords is None:
            coords = self.guess_map_coordinates(kw_coords)
        slices = [kw_coords[name] for name in coords]
        values = [self.coords[name][kw_coords[name]]
                  for name in coords]

        c = ax.contour(*values, frame, **kwargs)
        if limits:
            self.set_limits(ax, *slices)

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
        """
        if variable is None:
            variable = self.last_plot
        kw_coords = self.get_coords_full(**kw_coords)
        kw_coords = self._get_coords_none_previous(**kw_coords)
        frame = self.select(variable, **kw_coords)

        self.set_plot_keys(variable, **kw_coords)

        if coords is None:
            coords = [name for name, key in kw_coords.key()
                      if self.coords[name][key].size > 1]
        values = [self.coords[name][kw_coords[name]]
                  for name in coords]

        for coll in c.collections:
            ax.collections.remove(coll)
        c = ax.contour(*values, frame, **kwargs)

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

            im = dt.imshow(ax, var, coords=None, kwargs=im_kw, **kwargs)
            title = dt.vi.get_attr_safe('fullname', var, default=var)
            ax.set_title(title)

            divider = make_axes_locatable(ax)
            cax = divider.append_axes("right", "2%", 0)
            label = dt.vi.get_attr_safe('units', var, default='')

            ax.get_figure().colorbar(im, cax=cax, label=label)

            return im

        images = self.iter_axes(axes, plot, variables, coords,
                                limits=limits, kwargs=kwargs, **kw_coords)
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

    def iter_axes(self, axes, func, variables=None, iterables=None, **kwargs):
        """Apply function over multiple axes.

        Parameters
        ----------
        axes: Array of Matplotlib axis
            Axes to iterate on.
        func: Callable
            Function to call for every axe.
            func(ax, DataPlot, variable, *iterable, **kwargs)
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
                output[i] = func(ax, self, var, *iterable, **kwargs)

        self.set_plot_keys(variables)
        output = np.array(output)
        output = np.reshape(output, axes.shape)
        return output

    def hoevmuller(self):
        pass

    # TODO: hoevmuller plot
