"""Plot evolution of a variable against one coordinate."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import List

import matplotlib.lines

from tomate.coordinates.time import Time
from tomate.custom_types import Array, KeyLikeInt
from tomate.db_types.plotting.plot_object import PlotObjectABC


class PlotObjectLine(PlotObjectABC):
    """Plot a variables against a coordinate.

    See also
    --------
    matplotlib.axes.Axes.plot: Function used.
    """

    DIM = 1

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
            raise IndexError(f"Number of axes not 2 ({axes_})")

        if axes_[0] in self.scope.coords:
            self.var_idx = 1
        else:
            self.var_idx = 0

        return axes_

    def _get_data(self) -> Array:
        return self.db.view_selected(self.scope)

    def create_plot(self):
        data = self.get_data()

        dim = self.scope[self.axes[1-self.var_idx]]
        if isinstance(dim, Time):
            data_dim = dim.index2date(pydate=True)
        else:
            data_dim = dim[:]
        to_plot = [data_dim, data]
        if self.var_idx != 1:
            to_plot.reverse()
        self.object, = self.ax.plot(*to_plot, **self.kwargs)

    def update_plot(self, **keys: KeyLikeInt):
        self.update_scope(**keys)
        x = self.scope[self.axes[1-self.var_idx]]
        y = self.get_data()
        if self.var_idx != 1:
            x, y = y, x
        self.object.set_xdata(x)
        self.object.set_ydata(y)
