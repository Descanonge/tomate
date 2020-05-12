"""Contour objects for contours."""

from data_loader.db_types.plotting.plot_object import PlotObjectABC


class PlotObjectContour(PlotObjectABC):

    @property
    def contour(self):
        return self.object

    def _get_data(self):
        image = self.db.view_ordered(self.axes[1::-1],
                                     keyring=self.keyring)
        return image

    def find_axes(self, axes=None):
        if axes is not None:
            axes_ = axes
            if len(axes_) not in [2, 3]:
                raise ValueError("Number of axes supplied not 2 or 3"
                                 " (supplied %s)" % axes_)
        else:
            axes_ = self.keyring.get_high_dim()[::-1]
            if len(axes_) != 2:
                raise IndexError("Number of axis found is not 2"
                                 " (found %s)" % axes_)
        if len(axes_) == 2:
            axes_.append(self.scope.var[0])

    def create_plot(self):
        image = self.get_data()
        coords = [self.scope[name][:]
                  for name in self.coords]
        self.object = self.ax.contour(*coords, image, **self.kwargs)

    def remove(self):
        for coll in self.contour.collections:
            self.ax.collections.remove(coll)
        self.object = None

    def set_limits(self):
        for x, dim in zip([True, False], self.axes[:2]):
            self._set_limits_dim(dim, x)
