"""Abstract object containing information about plots."""

from typing import Any, Dict, List, Union, TYPE_CHECKING

from matplotlib.axes import Axes

from data_loader.custom_types import KeyLikeInt
from data_loader.keys.keyring import Keyring
from data_loader.scope import Scope

if TYPE_CHECKING:
    from data_loader.db_types.plotting.data_plot import DataPlot


class PlotObjectABC():
    """Object containing information about plots."""

    def __init__(self, db: 'DataPlot', ax: Axes,
                 scope: Scope, coords: List[str],
                 data, **kwargs):
        self.db = db
        self.ax = ax
        self.scope = scope
        self.object = None
        self.data = data
        self.coords = coords
        self.kwargs = kwargs

    def _up_scope(self, keyring=None, **keys):
        scope = self.db.get_subscope(self.scope, keyring=keyring,
                                     int2list=False, **keys)
        self.scope = scope

    def _up_scope_by_value(self, keyring=None, **keys):
        scope = self.db.get_subscope_by_value(self.scope,
                                              keyring=keyring,
                                              int2list=False, **keys)
        self.scope = scope

    def get_data(self):
        if self.data is not None:
            return self.data
        return self._get_data()

    def _get_data(self):
        raise NotImplementedError()

    @classmethod
    def create(cls, db: 'DataPlot', ax: Axes,
               scope: Union[str, Scope] = 'loaded',
               coords: List[str] = None,
               data=None,
               kwargs: Dict[str, Any] = None,
               **keys: KeyLikeInt):
        scope = db.get_scope(scope).copy()
        scope.slice(**keys, int2list=False)

        if coords is None:
            coords = scope.parent_keyring.get_high_dim()
        if kwargs is None:
            kwargs = {}

        po = cls(db, ax, scope, coords, data, **kwargs)
        return po

    def set_kwargs(self, replace=True, **kwargs):
        if replace:
            self.kwargs.update(kwargs)
        else:
            kwargs.update(self.kwargs)
            self.kwargs = kwargs

    def set_plot(self, *args, **keys):
        raise NotImplementedError()

    def remove(self):
        raise NotImplementedError()

    def update_plot(self, *args, **keys):
        raise NotImplementedError()

    def set_limits(self):
        set_limits(self.ax, self.scope, self.coords)


def set_limits(ax, scope, coords=None, keyring=None, **keys):
    keyring = Keyring.get_default(keyring, **keys)
    if coords:
        names = coords
    elif keyring:
        names = keyring.dims[:2]
    else:
        names = [c.name for c in scope.coords if c.size > 1]
    keyring.make_full(names)
    keyring.make_total()
    axes = [ax.xaxis, ax.yaxis]
    for axis, name in zip(axes[:len(names)], names):
        limits = scope[name].get_limits(keyring[name].value)
        axis.set_view_interval(*limits)
