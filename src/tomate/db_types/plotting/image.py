"""Plot object for images."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import matplotlib.image

from tomate.custom_types import KeyLikeInt
from tomate.db_types.plotting.image_abc import PlotObjectImageABC


class PlotObjectImage(PlotObjectImageABC):
    """Plot object for images.

    See also
    --------
    matplotlib.axes.Axes.imshow: Function used.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_kwargs(origin='lower')

    @property
    def image(self) -> matplotlib.image.AxesImage:
        """Matplotlib image object."""
        return self.object

    def create_plot(self):
        image = self.get_data()
        extent = self.scope.get_extent(*self.axes[:2])
        self.object = self.ax.imshow(image, extent=extent, **self.kwargs)

    def update_plot(self, **keys: KeyLikeInt):
        self.up_scope(**keys)
        image = self.get_data()
        self.image.set_data(image)
        self.image.set_extent(self.scope.get_extent(*self.axes[:2]))
