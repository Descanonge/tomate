"""Abstract class for 2D plot."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import List

from tomate.custom_types import Array
from tomate.db_types.plotting.plot_object import PlotObjectABC


class PlotObjectImageABC(PlotObjectABC):
    """Plot object for 2D images plot."""

    DIM = 2

    def _get_data(self) -> Array:
        image = self.db.view_ordered(self.axes[1::-1],
                                     keyring=self.keyring)
        return image

    def find_axes(self, axes: List[str] = None) -> List[str]:
        if axes is not None:
            axes_ = axes
            if len(axes_) not in [2, 3]:
                raise ValueError("Number of axes supplied not 2 or 3"
                                 f" (supplied {axes_})")
        else:
            axes_ = self.keyring.get_high_dim()[::-1]

        if len(axes_) == 2:
            axes_.append(self.scope.var[0])

        return axes_

    def set_limits(self):
        """Change axis limits to data."""
        self.ax.set_xlim(*self.get_limits(self.axes[0]))
        self.ax.set_ylim(*self.get_limits(self.axes[1]))
        self.image.set_clim(*self.get_limits(self.axes[2]))
