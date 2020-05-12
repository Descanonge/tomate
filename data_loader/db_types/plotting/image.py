"""Plot object for images."""


from data_loader.db_types.plotting.plot_object import PlotObjectABC
from data_loader.keys.keyring import Keyring


class PlotObjectImage(PlotObjectABC):

    DIM = 2

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_kwargs(origin='lower')

    @property
    def image(self):
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

        if len(axes_) == 2:
            axes_.append(self.scope.var[0])

        return axes_

    def create_plot(self):
        image = self.get_data()
        extent = self.scope.get_extent(*self.axes[:2])
        self.object = self.ax.imshow(image, extent=extent, **self.kwargs)

    def update_plot(self, **keys):
        self.up_scope(**keys)
        image = self.get_data()
        self.image.set_data(image)
        self.image.set_extent(self.scope.get_extent(*self.axes[:2]))

    def set_limits(self):
        for x, dim in zip([True, False], self.axes[:2]):
            self._set_limits_dim(dim, x)
