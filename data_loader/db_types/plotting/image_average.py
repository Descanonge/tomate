"""Plot 2D average of data."""

from typing import List

from data_loader.db_types.plotting.average_abc import PlotObjectAvgABC
from data_loader.db_types.plotting.image import PlotObjectImage


class PlotObjectImageAvg(PlotObjectAvgABC, PlotObjectImage):
    """Plot 2D average of data."""

    def find_axes(self, axes: List[str] = None) -> List[str]:
        if axes is not None:
            axes_ = axes
        else:
            axes_ = [d for d in self.keyring.get_high_dim()
                     if d not in self.avg_dims]

        if len(axes_) == 2:
            axes_.append(self.scope.var[0])

        if len(axes_) != 3:
            raise IndexError("Number of axes not 3 (%s)" % axes_)

        return axes_