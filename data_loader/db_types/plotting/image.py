"""Plot object for images."""


from data_loader.db_types.plotting.image_abc import PlotObjectImageABC
from data_loader.keys.keyring import Keyring


class PlotObjectImage(PlotObjectImageABC):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_kwargs(origin='lower')

    @property
    def image(self):
        return self.object

    def create_plot(self):
        image = self.get_data()
        extent = self.scope.get_extent(*self.axes[:2])
        self.object = self.ax.imshow(image, extent=extent, **self.kwargs)

    def update_plot(self, **keys):
        self.up_scope(**keys)
        image = self.get_data()
        self.image.set_data(image)
        self.image.set_extent(self.scope.get_extent(*self.axes[:2]))

