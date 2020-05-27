"""Abstract object containing information about plots."""

from typing import Any, Dict, List, Union, TYPE_CHECKING

from matplotlib.axes import Axes

from data_loader.custom_types import Array, KeyLikeInt, KeyLikeValue
from data_loader.keys.key import KeyValue
from data_loader.keys.keyring import Keyring
from data_loader.scope import Scope

if TYPE_CHECKING:
    from data_loader.db_types.plotting.data_plot import DataPlot


class PlotObjectABC():
    """Object containing information about plots.

    And methods for acting on that plot.
    Subclasses are to be made for different types of plot object,
    such as lines, 2D images, contours, ...

    Attributes
    ----------
    DIM: int
        Dimension of the data to plot.

    db: DataBase
    ax: matplotlib.axes.Axes
    scope: Scope
        Scope of plotted data.
        If data is to be fetched from database, ought to be a
        child of its loaded scope, its parent keyring should
        have the correct dimension.
    object: Any
        Object returned by matplotlib.
    data: Optional[Array]
        If not None, data to use (instead of fetching it
        from database).
    axes: List[str]
        Dimensions and variables name, in order of axes
        (x, y, [z], [color]).
    dict: Dict[Any]
        Keyword arguments to use for creating plot.
    """

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
    def keyring(self) -> Keyring:
        """Keyring to use for fetching data."""
        return self.scope.parent_keyring

    def up_scope(self, **keys: KeyLikeInt):
        """Update some dimensions scope.

        Only change specified dimensions.
        Acts on the parent scope of `scope` attribute.
        """
        keyring = self.keyring
        for dim, key in keys.items():
            keyring[dim] = key
        self.reset_scope(keyring)

    def up_scope_by_value(self, **keys: KeyLikeValue):
        """Update some dimensions scope by value.

        Only change specified dimensions.
        Acts on the parent scope of `scope` attribute.
        """
        keys_ = {}
        for dim, key in keys.items():
            keys_[dim] = KeyValue(key).apply(self.scope.dims[dim])
        self.up_scope(**keys_)

    def reset_scope(self, keyring: Keyring = None, **keys: KeyLikeInt):
        """Reset scope.

        Acts on the parent scope of `scope` attribute.
        """
        scope = self.db.get_subscope(self.scope.parent_scope,
                                     keyring=keyring,
                                     int2list=False, **keys)
        self.scope = scope

    def reset_scope_by_value(self, **keys: KeyLikeValue):
        """Reset scope.

        Acts on the parent scope of `scope` attribute.
        """
        scope = self.db.get_subscope_by_value(self.scope.parent_scope,
                                              int2list=False, **keys)
        self.scope = scope

    def get_data(self) -> Array:
        """Retrieve data for plot.

        Either from `data` attribute if specified, or
        from database.
        """
        if self.data is not None:
            return self.data
        self.check_keyring()
        return self._get_data()

    def _get_data(self) -> Array:
        """Retrieve data from database."""
        raise NotImplementedError()

    def check_keyring(self):
        """Check if keyring has correct dimension.
       
        :raises IndexError:
        """
        dim = len(self.keyring.get_high_dim())
        if dim != self.DIM:
            raise IndexError("Data to plot does not have right dimension"
                             " (is %d, expected %d)" % (dim, self.DIM))

    def find_axes(self, axes: List[str] = None) -> List[str]:
        """Get list of axes.

        Find to what correspond the figures axes from plot object keyring.

        :param axes: [opt] Supply axes instead of guessing from keyring.
        """
        raise NotImplementedError()

    @classmethod
    def create(cls, db: 'DataPlot', ax: Axes,
               scope: Union[str, Scope] = 'loaded',
               axes: List[str] = None,
               data=None,
               kwargs: Dict[str, Any] = None,
               **keys: KeyLikeInt):
        """Create plot object."""
        scope = db.get_subscope(scope, name='plotted').copy()
        scope.slice(**keys, int2list=False)

        if kwargs is None:
            kwargs = {}
        po = cls(db, ax, scope, axes, data, **kwargs)
        po.axes = po.find_axes(axes)
        return po

    def set_kwargs(self, replace: bool = True, **kwargs: Any):
        """Set plot options.

        :param replace: If True (default), overwrite options already stored
        """
        if replace:
            self.kwargs.update(kwargs)
        else:
            kwargs.update(self.kwargs)
            self.kwargs = kwargs

    def set_plot(self):
        """Create or update plot."""
        if self.object is None:
            self.create_plot()
        else:
            self.update_plot()

    def create_plot(self):
        """Plot data."""
        raise NotImplementedError()

    def remove(self):
        """Remove plot from axes."""
        self.object.remove()
        self.object = None

    def update_plot(self, **keys: KeyLikeInt):
        """Update plot.

        :param keys: Keys to change, as for `up_scope`.
        """
        self.up_scope(**keys)
        self.remove()
        self.create_plot()

    def set_limits(self):
        """Change axis limits to data."""
        raise NotImplementedError()

    def _set_limits_coord(self, coord: str, x: bool = True):
        """Set limits if the axis is for a coordinate.

        :param x: For the x-axis if True, y-axis otherwise.
        """
        limits = self.scope[coord].get_limits()
        if x:
            self.ax.set_xlim(*limits)
        else:
            self.ax.set_ylim(*limits)

    def _set_limits_var(self, var: str, x: bool = True):
        """Set limits if the axis is for a variable.

        Use the database VI attributes 'vmin' and 'vmax' if
        available.

        :param x: For the x-axis if True, y-axis otherwise.
        """
        vmin = self.db.vi.get_attr_safe(var, 'vmin')
        vmax = self.db.vi.get_attr_safe(var, 'vmax')
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
