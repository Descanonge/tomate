"""Plot a variable against another."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import numpy as np

from typing import List, Optional

from tomate.custom_types import Array
from tomate.db_types.plotting.plot_object import PlotObjectABC


class PlotObjectScatter(PlotObjectABC):
    """Plot a variable against another.


    :attr sizes: Union[None, float, Sequence[float]]:
        See `s` argument of scatter.
    :attr colors: Union[None, str, Sequence[float], Sequence[str]]:
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
            raise IndexError(f"Number of not 2 ({axes_})")

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

    def update_plot(self, **keys):
        self.up_scope(**keys)
        self.object.set_offsets(np.column_stack(self.get_data()))
        sizes = self.get_sizes()
        colors = self.get_colors()
        if sizes is not None:
            self.object.set_sizes(sizes)
        if colors is not None:
            self.object.set_facecolor(self.object.to_rgba(colors))
