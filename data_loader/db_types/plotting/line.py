"""Plot evolution of a variable against one dimension."""

from data_loader.db_types.plotting.plot_object import PlotObjectABC


class PlotObjectLine(PlotObjectABC):

    DIM = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.axis_var = 0

    @property
    def line(self):
        return self.object

    def find_axes(self, axes=None):
        if axes is not None:
            axes_ = axes
        else:
            axes_ = [self.keyring.get_high_dim()[0], self.scope.var[0]]

        if len(axes_) != 2:
            raise IndexError("Number of axes not 2 (is %d)" % len(axes_))

        if axes_[0] in self.scope.coords:
            self.axis_var = 1

        return axes_

    def _get_data(self):
        data = [None, None]
        data[self.axis_var] = self.db.view_selected(self.scope)
        data[1-self.axis_var] = self.scope[self.axes[1-self.axis_var]][:]
        return data

    def create_plot(self):
        data = self.get_data()
        self.object, = self.ax.plot(*data, **self.kwargs)

    def update_plot(self, **keys):
        self.up_scope(**keys)
        _, line = self.get_data()
        self.line.set_ydata(line)

    def set_limits(self):
        self._set_limits_var(self.axes[self.axis_var], x=self.axis_var == 0)
        self._set_limits_coord(self.axes[1-self.axis_var], x=self.axis_var == 1)
