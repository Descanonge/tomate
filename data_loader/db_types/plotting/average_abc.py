"""Abstract plot object for plotting averages."""

from typing import List

from data_loader.db_types.plotting.plot_object import PlotObjectABC


class PlotObjectAvgABC(PlotObjectABC):
    """Plot average of data.

    DataCompute is necessary as a base for computing
    average.

    :attr avg_dims: List[str]: Dimensions to average along.

    See also
    --------
    data_loader.db_types.data_compute.DataCompute.mean: Function used.
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
                             " (is %d, expected %d)" % (dim, self.DIM))

    def _get_data(self):
        if 'DataCompute' not in self.db.bases:
            raise TypeError("DataComptue necessary for averaging.")
        data = self.db.mean(self.avg_dims, **self.keyring.kw)
        return data
