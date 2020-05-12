"""Abstract class for 2D plot."""

from typing import List

from data_loader.custom_types import Array
from data_loader.db_types.plotting.plot_object import PlotObjectABC


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
                                 " (supplied %s)" % axes_)
        else:
            axes_ = self.keyring.get_high_dim()[::-1]

        if len(axes_) == 2:
            axes_.append(self.scope.var[0])

        return axes_

    def set_limits(self):
        for x, coord in zip([True, False], self.axes[:2]):
            self._set_limits_coord(coord, x)
