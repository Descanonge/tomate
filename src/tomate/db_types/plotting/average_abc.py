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
            raise TypeError("DataCompute necessary for averaging.")
        keyring = self.keyring.copy()
        var = self.scope.var.get_str_name(keyring.pop('var').value)
        data = self.db.mean(var, self.avg_dims, **keyring.kw)

        # Nothing to reorder
        if self.DIM == 1:
            return data

        axes = [d for d in self.db[var].dims if d not in self.avg_dims]
        target = self.axes[:2][::-1]
        data = self.db[var].acs.reorder(axes, data, target)
        return data
