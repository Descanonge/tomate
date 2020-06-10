"""Add convenience functions for plotting data."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import Any, Dict, List, Tuple
import logging

import numpy as np
from matplotlib.axes import Axes

from tomate.custom_types import Array, KeyLikeInt, KeyLikeVar
from tomate.data_base import DataBase

from tomate.db_types.plotting.contour import PlotObjectContour
from tomate.db_types.plotting.image import PlotObjectImage
from tomate.db_types.plotting.image_average import PlotObjectImageAvg
from tomate.db_types.plotting.line import PlotObjectLine
from tomate.db_types.plotting.line_average import PlotObjectLineAvg
from tomate.db_types.plotting.scatter import PlotObjectScatter


log = logging.getLogger(__name__)


class DataPlot(DataBase):
    """Added functionalities for plotting data."""

    def plot(self, ax: Axes, variable: KeyLikeVar,
             data: Array = None, axes: List[str] = None,
             plot: bool = True, limits: bool = True,
             kwargs: Dict[str, Any] = None,
             **keys: KeyLikeInt) -> PlotObjectLine:
        """Plot evolution of a variable against a dimension.

        Creates a plot object and eventually plots data.

        :param ax: Matplotlib axis to plot upon.
        :param variable: Variable to plot.
        :param data: [opt] Data to plot. If not specified, data
            is fetched from loaded scope using `keys`.
        :param axes: [opt] Dimension or variable to put on what axis
            (X-axis, then Y-axis, and eventually Z-axis (colors))
            If not supplied, the plot object will do its best to guess
            what goes on which axis from what data is selected for plotting.
            This is not always possible !
        :param plot: Draw the plot if True (default).
        :param limits: Change axis limits to data limits if True (default).
        :param kwargs: [opt] Keywords arguments to pass to plotting function.
        :param keys: Select part of data to plot.
            Selected data should have correct dimension (here 1D).

        See also
        --------
        matplotlib.axes.Axes.plot: Function used.
        """
        self.check_loaded()
        po = PlotObjectLine.create(self, ax, data=data, axes=axes, kwargs=kwargs,
                                   var=variable, **keys)
        if plot:
            po.create_plot()
        if limits:
            po.set_limits()

        return po

    def imshow(self, ax: Axes, variable: KeyLikeVar,
               data: Array = None, axes: List[str] = None,
               plot: bool = True, limits: bool = True,
               kwargs: Dict[str, Any] = None,
               **keys: KeyLikeInt) -> PlotObjectImage:
        """Plot variable as 2D image.

        See also
        --------
        DataPlot.plot: For more details on arguments.
        matplotlib.axes.Axes.imshow: Function used.
        """
        self.check_loaded()
        po = PlotObjectImage.create(self, ax, data=data, axes=axes, kwargs=kwargs,
                                    var=variable, **keys)
        if plot:
            po.create_plot()
        if limits:
            po.set_limits()

        return po

    def contour(self, ax: Axes, variable: KeyLikeVar,
                data: Array = None, axes: List[str] = None,
                plot: bool = True, limits: bool = True,
                kwargs: Dict[str, Any] = None,
                **keys: KeyLikeInt) -> PlotObjectContour:
        """Plot variable as contours.

        See also
        --------
        DataPlot.plot: For more details on arguments.
        matplotlib.axes.Axes.imshow: Function used.
        """
        self.check_loaded()
        po = PlotObjectContour.create(self, ax, data=data, axes=axes, kwargs=kwargs,
                                      var=variable, **keys)
        if plot:
            po.create_plot()
        if limits:
            po.set_limits()

        return po

    def scatter(self, ax: Axes, variable1: str, variable2: str,
                data: Tuple[Array, Array] = None,
                sizes=None, colors=None,
                plot: bool = True, limits: bool = True,
                kwargs: Dict[str, Any] = None,
                **keys: KeyLikeInt) -> PlotObjectScatter:
        """Plot a variable against another.

        :param variable1: Variable on X-axis
        :param variable2: Variable on Y-axis
        :param sizes: Sizes of markers. If a variable name is used,
            data is fetched from database. Otherwise the argument is
            send as is to scatter.
        :param colors: Colors of markers. If a variable name is used,
            data is fetched from database. Otherwise the argument is
            send as is to scatter.

        See also
        --------
        DataPlot.plot: For more details on arguments.
        matplotlib.axes.Axes.scatter: Function used.
        """
        self.check_loaded()
        if kwargs is None:
            kwargs = {}
        kwargs['sizes'] = sizes
        kwargs['colors'] = colors
        po = PlotObjectScatter.create(self, ax, data=data,
                                      axes=[variable1, variable2],
                                      kwargs=kwargs, **keys)
        if plot:
            po.create_plot()
        if limits:
            po.set_limits()

        return po

    def plot_avg(self, ax: Axes, variable: KeyLikeInt,
                 data: Array = None, axes: List[str] = None,
                 avg_dims: List[str] = None,
                 plot: bool = True, limits: bool = True,
                 kwargs: Dict[str, Any] = None,
                 **keys: KeyLikeInt) -> PlotObjectLineAvg:
        """Plot evolution of average of a variable against a dimension.

        Selected data once averaged should be of dimension 1.
        Needs DataCompute base for computing average.

        :param avg_dims: List of dimensions to average along.

        See also
        --------
        DataPlot.plot: For more details on arguments.
        matplotlib.axes.Axes.plot: Function used.
        tomate.db_types.data_compute.DataCompute.mean: Function used for averaging.
        """
        self.check_loaded()
        if kwargs is None:
            kwargs = {}
        kwargs['avg_dims'] = avg_dims
        po = PlotObjectLineAvg.create(self, ax, data=data, axes=axes,
                                      kwargs=kwargs,
                                      var=variable, **keys)
        if plot:
            po.create_plot()
        if limits:
            po.set_limits()

        return po

    def imshow_avg(self, ax: Axes, variable: KeyLikeVar,
                   data: Array = None, axes: List[str] = None,
                   avg_dims: List[str] = None,
                   plot: bool = True, limits: bool = True,
                   kwargs: Dict[str, Any] = None,
                   **keys: KeyLikeInt) -> PlotObjectImageAvg:
        """Plot image of average of a variable against a dimension.

        Selected data once averaged should be of dimension 2.
        Needs DataCompute base for computing average.

        :param avg_dims: List of dimensions to average along.

        See also
        --------
        DataPlot.plot: For more details on arguments.
        matplotlib.axes.Axes.imshow: Function used.
        tomate.db_types.data_compute.DataCompute.mean: Function used for averaging.
        """
        self.check_loaded()
        if kwargs is None:
            kwargs = {}
        kwargs['avg_dims'] = avg_dims
        po = PlotObjectImageAvg.create(self, ax, data=data, axes=axes,
                                       kwargs=kwargs,
                                       var=variable, **keys)
        if plot:
            po.create_plot()
        if limits:
            po.set_limits()

        return po


class _DataPlot_(DataBase):
    """Added functionalities for plotting data."""

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

            # if _has_matplotlib:
            #     divider = make_axes_locatable(ax)
            #     cax = divider.append_axes("right", "2%", 0)
            #     label = dt.vi.get_attr_safe('units', var, default='')
            #     ax.get_figure().colorbar(im, cax=cax, label=label)

            return im

        if variables is None:
            variables = self.loaded.var[:]
        images = self.iter_axes(axes, plot, variables,
                                limits=limits, kwargs=kwargs, coords=coords,
                                **kw_coords)
        self.plotted = self.get_subscope('loaded', var=variables, **kw_coords)
        return images

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

    def plot_histogram(self, ax, variable, kwargs=None, **keys):
        if kwargs is None:
            kwargs = {}

        kw = {'density': True}
        kw.update(kwargs)
        data = self.view(variable, **keys).compressed()
        ax.hist(data, **kw)
