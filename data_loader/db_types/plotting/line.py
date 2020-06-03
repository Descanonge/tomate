"""Plot evolution of a variable against one coordinate."""

from typing import List

import matplotlib.lines

from data_loader.custom_types import Array, KeyLikeInt
from data_loader.db_types.plotting.plot_object import PlotObjectABC


class PlotObjectLine(PlotObjectABC):
    """Plot a variables against a coordinate.

    Attributes
    ----------
    axis_var: int
        Place of variable in axes (0 if variable is on X, 1 if on Y)

    See also
    --------
    matplotlib.axes.Axes.plot: Function used.
    """

    DIM = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.axis_var = 0

    @property
    def line(self) -> matplotlib.lines.Line2D:
        """Matplotlib line."""
        return self.object

    def find_axes(self, axes: List[str] = None) -> List[str]:
        if axes is not None:
            axes_ = axes
        else:
            axes_ = [self.keyring.get_high_dim()[0], self.scope.var[0]]

        if len(axes_) != 2:
            raise IndexError("Number of axes not 2 (%s)" % axes_)

        if axes_[0] in self.scope.coords:
            self.axis_var = 1
        else:
            self.axis_var = 0

        return axes_

    def _get_data(self) -> Array:
        return self.db.view_selected(self.scope)

    def create_plot(self):
        data = self.get_data()
        dim = self.scope[self.axes[1-self.axis_var]]
        to_plot = [dim, data]
        if self.axis_var != 1:
            to_plot.reverse()
        self.object, = self.ax.plot(*to_plot, **self.kwargs)

    def update_plot(self, **keys: KeyLikeInt):
        self.up_scope(**keys)
        x = self.scope[self.axes[1-self.axis_var]]
        y = self.get_data()
        if self.axis_var != 1:
            x, y = y, x
        self.object.set_xdata(x)
        self.object.set_ydata(y)
