"""Contour objects for contours."""

from data_loader.db_types.plotting.image_abc import PlotObjectImageABC


class PlotObjectContour(PlotObjectImageABC):

    @property
    def contour(self):
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
