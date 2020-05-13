"""Plot a variable against another."""

import numpy as np
import numpy.ma

from typing import List, Optional

from data_loader.custom_types import Array
from data_loader.db_types.plotting.plot_object import PlotObjectABC


class PlotObjectScatter(PlotObjectABC):
    """Plot a variable against another.

    Attributes
    ----------

    sizes: Union[None, float, Sequence[float]]
        See `s` argument of scatter.
    colors: Union[None, str, Sequence[float], Sequence[str]]
        See `c` argument of scatter.

    See also
    --------
    matplotlib.axes.Axes.scatter: Function used.
    """

    DIM = 1

    def __init__(self, *args,
                 sizes: str = None,
                 colors: str = None,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.sizes = sizes
        self.colors = colors

    def find_axes(self, axes: List[str] = None) -> List[str]:
        if axes is not None:
            axes_ = axes
        else:
            raise TypeError("No axes supplied.")

        if len(axes_) != 2:
            raise IndexError("Number of not 2 (%s)" % axes_)

        return axes_

    def check_keyring(self):
        pass

    def _get_data(self) -> List[Array]:
        data = [self.db.view_selected(self.scope, var=var)
                for var in self.axes]
        for i, d in enumerate(data):
            data[i] = d.flatten()
        return data

    def get_sizes(self) -> Optional[Array]:
        """Get sizes."""
        if isinstance(self.sizes, str) and self.sizes in self.scope.var:
            return self.db.view_selected(self.scope, var=self.sizes).flatten()
        return self.sizes

    def get_colors(self) -> Optional[Array]:
        """Get colors."""
        if isinstance(self.colors, str):
            return self.db.view_selected(self.scope, var=self.colors).flatten()
        return self.colors

    def create_plot(self):
        data = self.get_data()
        sizes = self.get_sizes()
        colors = self.get_colors()
        self.object = self.ax.scatter(*data, s=sizes, c=colors,
                                      **self.kwargs)

    def set_limits(self):
        self._set_limits_var(self.axes[0], True)
        self._set_limits_var(self.axes[1], False)

    def update_plot(self, **keys):
        self.up_scope(**keys)
        self.object.set_offsets(np.column_stack(self.get_data()))
        sizes = self.get_sizes()
        colors = self.get_colors()
        if sizes is not None:
            self.object.set_sizes(sizes)
        if colors is not None:
            self.object.set_facecolor(self.object.to_rgba(colors))
