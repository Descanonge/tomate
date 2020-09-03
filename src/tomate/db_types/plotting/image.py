"""Plot object for images."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import List

import matplotlib.image

from tomate.coordinates.time import Time
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
        self.object = self.ax.imshow(image, extent=self._get_extent(),
                                     **self.kwargs)

    def update_plot(self, **keys: KeyLikeInt):
        self.update_scope(**keys)
        image = self.get_data()
        self.image.set_data(image)
        self.image.set_extent(self._get_extent())

    def _get_extent(self) -> List[float]:
        extent = []
        for name in self.axes[:2]:
            dim = self.scope[name]
            if isinstance(dim, Time):
                extent += dim.change_units_other(dim[[0, -1]], dim.units,
                                                 'days since 01-01-01').tolist()
            else:
                extent += dim.get_extent()
        return extent
