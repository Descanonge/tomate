"""Add convenience functions for plotting data."""

import logging

from data_loader.data_base import DataBase


log = logging.getLogger(__name__)


class DataPlot(DataBase):
    """Added functionalities for plotting data.

    Attributes
    ----------
    variables_plot: List[str]
    slices_plot: Dict
        What part of the data have been plotted.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.variables_plot = []
        self.slices_plot = {}
        for name, key in self.slices.items():
            try:
                k = key.copy()
            except AttributeError:
                k = key
            self.slices_plot[name] = k

    def _get_none_previous(self, **kw_coords):
        for name, key in kw_coords.items():
            if key is None:
                kw_coords[name] = self.slices_plot[name]
        return kw_coords

    @staticmethod
    def _get_none_single(idx=0, **kw_coords):
        for name, key in kw_coords.items():
            if key is None:
                kw_coords[name] = idx
        return kw_coords

    def set_plot_keys(self, variable=None, **kw_coords):
        if variable is not None:
            if not isinstance(variable, list):
                variable = [variable]
            self.variables_plot = variable

        for name, key in kw_coords.items():
            self.slices_plot[name] = key

    def set_limits(self, ax, *coords, **kw_coords):
        """Set axis limits."""
        if len(coords) + len(kw_coords) > 2:
            log.warning('Only first two arguments will be used.')

        keys = {}
        for i, key in enumerate(coords[:2]):
            keys[['lon', 'lat'][i]] = key

        for name, key in kw_coords.items():
            if len(keys) > 2:
                break
            keys[name] = key

        for i in range(len(keys), 2):
            if 'lon' not in keys:
                keys['lon'] = None
            if 'lat' not in keys:
                keys['lat'] = None

        kw_coords = self.get_none_total(**keys)
        names = list(kw_coords.keys())
        ax.set_xlim(*self.coords[names[0]].get_limits(kw_coords[names[0]]))
        ax.set_ylim(*self.coords[names[1]].get_limits(kw_coords[names[1]]))

    def imshow(self, ax, variable=None, limits=True, kwargs=None, **kw_coords):
        """Plot a frame on a heatmap."""
        self._check_loaded()

        if variable is None:
            variable = self.vi.var[0]

        kw_coords = self.get_coords_full(**kw_coords)
        keys_latlon = self.get_none_total(**{k: kw_coords[k]
                                             for k in ['lat', 'lon']})
        kw_coords.update(keys_latlon)
        kw_coords = self._get_none_single(**kw_coords)
        kw_coords = self.sort_by_coords(kw_coords)

        self.set_plot_keys(variable, **kw_coords)

        kwargs_def = {'origin': 'lower'}
        if kwargs is not None:
            kwargs_def.update(kwargs)
        kwargs = kwargs_def

        slice_lat = kw_coords['lat']
        slice_lon = kw_coords['lon']
        extent = self.lon.get_extent(slice_lat) + self.lat.get_extent(slice_lon)
        frame = self[variable][tuple(self.slices_plot.values())]

        im = ax.imshow(frame, extent=extent, **kwargs)

        if limits:
            self.set_limits(ax, slice_lon, slice_lat)

        return im

    def update_imshow(self, im, variable=None, **kw_coords):
        """Update a heatmap plot.

        If a parameter is None, the value used for setting
        the plot is used.
        """
        if variable is None:
            variable = self.variables_plot[0]
        kw_coords = self.get_coords_full(**kw_coords)
        kw_coords = self._get_none_previous(**kw_coords)
        kw_coords = self.sort_by_coords(kw_coords)

        self.set_plot_keys(variable, **kw_coords)

        frame = self[variable][tuple(kw_coords.values())]
        im.set_data(frame)

    def contour(self, ax, variable=None, limits=True, kwargs=None, **kw_coords):
        if variable is None:
            variable = self.vi.var[0]
        kw_coords = self.get_coords_full(**kw_coords)
        keys_latlon = self.get_none_total(**{k: kw_coords[k]
                                             for k in ['lat', 'lon']})
        kw_coords.update(keys_latlon)
        kw_coords = self._get_none_single(**kw_coords)
        kw_coords = self.sort_by_coords(kw_coords)

        self.set_plot_keys(variable, **kw_coords)

        slice_lat = kw_coords['lat']
        slice_lon = kw_coords['lon']
        frame = self[variable][tuple(kw_coords.values())]
        c = ax.contour(self.lon[slice_lon], self.lat[slice_lat],
                       frame, **kwargs)
        if limits:
            self.set_limits(ax, slice_lon, slice_lat)

        return c

    def update_contour(self, ax, c, variable=None, kwargs=None, **kw_coords):
        """Update a contour plot.

        If a parameter is None, the value used for setting
        the plot is used.
        """
        if variable is None:
            variable = self.variables_plot[0]
        kw_coords = self.get_coords_full(**kw_coords)
        kw_coords = self._get_none_previous(**kw_coords)
        kw_coords = self.sort_by_coords(kw_coords)

        self.set_plot_keys(variable, **kw_coords)

        slice_lat = kw_coords['lat']
        slice_lon = kw_coords['lon']
        frame = self[variable][tuple(kw_coords.values())]

        for coll in c.collections:
            ax.collections.remove(coll)

        c = ax.contour(self.lon[slice_lon], self.lat[slice_lat],
                       frame, **kwargs)

        return c

    # TODO: hoevmuller plot
