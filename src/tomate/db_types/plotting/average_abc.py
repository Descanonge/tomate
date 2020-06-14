"""Abstract plot object for plotting averages."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import List

from tomate.db_types.plotting.plot_object import PlotObjectABC


class PlotObjectAvgABC(PlotObjectABC):
    """Plot average of data.

    DataCompute is necessary as a base for computing
    average.

    :attr avg_dims: List[str]: Dimensions to average along.

    See also
    --------
    tomate.db_types.data_compute.DataCompute.mean: Function used.
    """

    def __init__(self, *args, avg_dims: List[str] = None,
                 **kwargs):
        super().__init__(*args, **kwargs)
        if avg_dims is None:
            avg_dims = []
        self.avg_dims = avg_dims

    def check_keyring(self):
        dim = len([d for d in self.keyring.get_high_dim()
                   if d not in self.avg_dims])
        if dim != self.DIM:
            raise IndexError("Data to plot does not have right dimension"
                             f" (is {dim}, expected {self.DIM})")

    def _get_data(self):
        if 'DataCompute' not in self.db.bases:
            raise TypeError("DataComptue necessary for averaging.")
        data = self.db.mean(self.avg_dims, **self.keyring.kw)
        return data
