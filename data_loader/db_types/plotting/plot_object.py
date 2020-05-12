"""Abstract object containing information about plots."""

from typing import Any, Dict, List, Union, TYPE_CHECKING

from matplotlib.axes import Axes

from data_loader.custom_types import KeyLikeInt, KeyLikeValue
from data_loader.keys.key import KeyValue
from data_loader.keys.keyring import Keyring
from data_loader.scope import Scope

if TYPE_CHECKING:
    from data_loader.db_types.plotting.data_plot import DataPlot


class PlotObjectABC():
    """Object containing information about plots."""

    DIM = 0

    def __init__(self, db: 'DataPlot', ax: Axes,
                 scope: Scope, axes: List[str],
                 data, **kwargs):
        self.db = db
        self.ax = ax
        self.scope = scope
        self.object = None
        self.data = data
        self.axes = axes
        self.kwargs = kwargs

    @property
    def keyring(self):
        return self.scope.parent_keyring

    def up_scope(self, **keys):
        keyring = self.keyring
        for dim, key in keys.items():
            keyring[dim] = key
        self.reset_scope(keyring)

    def up_scope_by_value(self, **keys):
        keys_ = {}
        for dim, key in keys.items():
            keys_[dim] = KeyValue(key).apply(self.scope.dims[dim])
        self.up_scope(**keys_)

    def reset_scope(self, keyring=None, **keys):
        scope = self.db.get_subscope(self.scope.parent_scope,
                                     keyring=keyring,
                                     int2list=False, **keys)
        self.scope = scope

    def reset_scope_by_value(self, **keys):
        scope = self.db.get_subscope_by_value(self.scope.parent_scope,
                                              int2list=False, **keys)
        self.scope = scope

    def get_data(self):
        if self.data is not None:
            return self.data
        self.check_keyring()
        return self._get_data()

    def _get_data(self):
        raise NotImplementedError()

    def check_keyring(self):
        dim = len(self.keyring.get_high_dim())
        if dim != self.DIM:
            raise IndexError("Data to plot does not have right dimension"
                             " (is %d, expected %d)" % (dim, self.DIM))

    def find_axes(self, axes=None):
        raise NotImplementedError()

    @classmethod
    def create(cls, db: 'DataPlot', ax: Axes,
               scope: Union[str, Scope] = 'loaded',
               axes: List[str] = None,
               data=None,
               kwargs: Dict[str, Any] = None,
               **keys: KeyLikeInt):
        scope = db.get_subscope(scope, name='plotted').copy()
        scope.slice(**keys, int2list=False)

        if kwargs is None:
            kwargs = {}
        po = cls(db, ax, scope, axes, data, **kwargs)
        po.axes = po.find_axes(axes)
        return po

    def set_kwargs(self, replace=True, **kwargs):
        if replace:
            self.kwargs.update(kwargs)
        else:
            kwargs.update(self.kwargs)
            self.kwargs = kwargs

    def set_plot(self):
        if self.object is None:
            self.create_plot()
        else:
            self.update_plot()

    def create_plot(self):
        raise NotImplementedError()

    def remove(self):
        self.object.remove()
        self.object = None

    def update_plot(self, **keys):
        self.up_scope(**keys)
        self.remove()
        self.create_plot()

    def set_limits(self):
        raise NotImplementedError()

    def _set_limits_dim(self, dim, x=True):
        limits = self.scope[dim].get_limits()
        if x:
            self.ax.set_xlim(*limits)
        else:
            self.ax.set_ylim(*limits)
        print('dim ', x, *limits)

    def _set_limits_var(self, var, x=True):
        vmin = self.db.vi.get_attr_safe(var, 'vmin')
        vmax = self.db.vi.get_attr_safe(var, 'vmax')
        print('var ', x, vmin, vmax)
        if x:
            self.ax.set_xlim(vmin, vmax)
        else:
            self.ax.set_ylim(vmin, vmax)

def set_limits_dim(ax, scope, axes=None, keyring=None, **keys):
    keyring = Keyring.get_default(keyring, **keys)
    if axes:
        names = axes
    elif keyring:
        names = keyring.dims[:2]
    else:
        names = [c.name for c in scope.coords if c.size > 1]
    keyring.make_full(names)
    keyring.make_total()
    funcs = [ax.set_xlim, ax.set_ylim]
    for f, name in zip(funcs[:len(names)], names):
        limits = scope[name].get_limits(keyring[name].value)
        f(*limits)
