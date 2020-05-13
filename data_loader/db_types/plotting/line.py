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
            raise IndexError("Number of axes not 2 (is %d)" % len(axes_))

        if axes_[0] in self.scope.coords:
            self.axis_var = 1

        return axes_

    def _get_data(self) -> Array:
        return self.db.view_selected(self.scope)

    def create_plot(self):
        data = self.get_data()
        self.object, = self.ax.plot(self.scope[self.axes[1-self.axis_var]], data,
                                    **self.kwargs)

    def update_plot(self, **keys: KeyLikeInt):
        self.up_scope(**keys)
        line = self.get_data()
        self.line.set_ydata(line)

    def set_limits(self):
        self._set_limits_var(self.axes[self.axis_var], x=self.axis_var == 0)
        self._set_limits_coord(self.axes[1-self.axis_var], x=self.axis_var == 1)
