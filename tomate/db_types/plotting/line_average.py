"""Plot evolution of average of a variable."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import List

from tomate.db_types.plotting.average_abc import PlotObjectAvgABC
from tomate.db_types.plotting.line import PlotObjectLine


class PlotObjectLineAvg(PlotObjectAvgABC, PlotObjectLine):
    """Plot evolution of average of a variable."""

    def find_axes(self, axes: List[str] = None) -> List[str]:
        if axes is not None:
            axes_ = axes
        else:
            dims = [d for d in self.keyring.get_high_dim()
                    if d not in self.avg_dims]
            axes_ = [dims[0], self.scope.var[0]]

        if len(axes_) != 2:
            raise IndexError(f"Number of axes not 2 ({axes_})")

        if axes_[0] in self.scope.coords:
            self.axis_var = 1

        return axes_
