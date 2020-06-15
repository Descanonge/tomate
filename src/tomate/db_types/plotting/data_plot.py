"""Add convenience functions for plotting data."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import Any, Callable, Dict, Iterable, List, Tuple
import logging

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from tomate.custom_types import Array, KeyLike, KeyLikeInt, KeyLikeVar
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

    def iter_axes(self, axes: Iterable[Axes], func: Callable,
                  iterables: Dict[str, Iterable] = None,
                  kwargs: Any = None) -> np.ndarray:
        r"""Apply function over multiple axes.

        :param axes: Axes to iterate on.
        func: Function to call for every axe.
            func(ax, DataPlot, args, kwargs, \*\*iterables)
        iterables: Keyword arguments passed to `func`,
            changing for every axis. Each iterable should be
            as least as long as the axes.
        kwargs: Passed to func.
        :returns: Array of objects returned from func.
            Same shape as `axes`.
        """
        if iterables is None:
            iterables = []
        if kwargs is None:
            kwargs = {}

        output = []
        axes = np.array(axes)
        for i, ax in enumerate(axes.flat):
            iter_i = {k: z[i] for k, z in iterables.items()}
            output.append(func(ax, self, **kwargs, **iter_i))

        output = np.array(output).reshape(axes.shape)
        return output

    def imshow_all(self, axes: Iterable[Axes], variables: List[str] = None,
                   imshow_axes: List[str] = None, limits: bool = True,
                   kwargs: Dict = None, **keys: KeyLike):
        """Plot all variables."""
        def plot(ax, db, **kwargs):
            var = kwargs.pop('var')
            if var is not None:
                po = db.imshow(ax, var, **kwargs)
                ax.set_title(db.vi.get_attr_safe('fullname', var, var))
                return po
            return None

        self.check_loaded()

        if variables is None:
            variables = self.loaded.var[:]
        axes = np.array(axes)
        for i in range(axes.size - len(variables)):
            variables.append(None)
        if kwargs is None:
            kwargs = {}
        plot_kw = {'axes': imshow_axes, 'limits': limits, 'kwargs': kwargs}
        plot_kw.update(keys)
        images = self.iter_axes(axes, plot, {'var': variables}, plot_kw)

        return images

    def del_axes_none(self, fig: Figure, axes: Iterable[Axes],
                      variables=None):
        """Delete axes for which variables is None.

        variables: List of variables. If element is None,
            axis will be removed from figure.
        """
        if variables is None:
            variables = self.loaded.var[:]

        variables = list(variables)
        axes = np.array(axes)

        for i in range(axes.size - len(variables)):
            variables.append(None)
        for i, var in enumerate(variables):
            if var is None:
                ax = axes.flat[i]
                fig.delaxes(ax)
