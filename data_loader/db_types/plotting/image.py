"""Plot object for images."""


from data_loader.db_types.plotting.plot_object import PlotObjectABC
from data_loader.keys.keyring import Keyring


class PlotObjectImage(PlotObjectABC):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kwargs = {'origin': 'lower'}

    @property
    def image(self):
        return self.object

    def _get_data(self):
        image = self.db.view_ordered(self.coords, keyring=self.scope.parent_keyring)
        if image.ndim != 2:
            raise IndexError("Selected data does not have the dimension"
                             " of an image %s" % list(image.shape))
        return image

    def create_plot(self):
        self.db.check_loaded()
        image = self.get_data()
        extent = self.scope.get_extent(*self.coords)
        self.object = self.ax.imshow(image, extent=extent, **self.kwargs)
