"""Plot objects for contours."""

import matplotlib.contour

from data_loader.db_types.plotting.image_abc import PlotObjectImageABC


class PlotObjectContour(PlotObjectImageABC):
    """Plot object for contours.

    See also
    --------
    matplotlib.axes.Axes.contour: Function used.
    """

    @property
    def contour(self) -> matplotlib.contour.QuadContourSet:
        """Matplotlib contour set."""
        return self.object

    def create_plot(self):
        image = self.get_data()
        coords = [self.scope[name][:]
                  for name in self.axes[:2]]
        self.object = self.ax.contour(*coords, image, **self.kwargs)

    def remove(self):
        for coll in self.contour.collections:
            self.ax.collections.remove(coll)
        self.object = None
