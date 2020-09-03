"""Abstract object containing information about plots."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import Any, Dict, List, Union, TYPE_CHECKING

from matplotlib.axes import Axes
from mpl_toolkits.axes_grid1 import make_axes_locatable

from tomate.coordinates.time import Time
from tomate.custom_types import Array, KeyLikeInt, KeyLikeValue
from tomate.keys.key import KeyValue
from tomate.keys.keyring import Keyring
from tomate.scope import Scope

if TYPE_CHECKING:
    from tomate.db_types.plotting.data_plot import DataPlot


class PlotObjectABC():
    """Object containing information about plots.

    And methods for acting on that plot.
    Subclasses are to be made for different types of plot object,
    such as lines, 2D images, contours, ...

    :attr db: DataBase:
    :attr scope: Scope: Scope of plotted data.
        If data is to be fetched from database, ought to be a child of its
        loaded scope, its parent keyring should have the correct dimension.
    :attr target_scope: Union[str, Scope]: Scope to fetch data from. Can
        be the name of a scope, in which case the corresponding scope from
        the database is used.

    :attr ax: matplotlib.axes.Axes:
    :attr cax: matplotlib.axes.Axes: Colorbar axis.
    :attr object: Any: Object returned by matplotlib.
    :attr colorbar: matplotlib.colorbar.Colorbar: Colorbar object.

    :attr data: Optional[Array]: If not None, data to use (instead of fetching
        it from database).
    :attr kwargs: Dict[Any]: Keyword arguments to use for creating plot.
    :attr axes: List[str]: Dimensions and variables name, in order of axes
        (x, y, [z], [color]).
    :attr var_idx: Union[int, List[int]]: Positions of plotted variables
        in `axes` attribute.
    """

    DIM = 0  #: Dimension of the data to plot.

    def __init__(self, db: 'DataPlot', ax: Axes,
                 scope: Scope, axes: List[str],
                 data, **kwargs):
        self.db = db
        self.scope = scope
        self._target_scope = scope

        self.data = data
        self.kwargs = kwargs
        self.axes = axes
        self.var_idx = None

        self.ax = ax
        self.object = None
        self.cax = None
        self.colorbar = None

    @property
    def keyring(self) -> Keyring:
        """Keyring to use for fetching data."""
        return self.scope.parent_keyring

    def update_scope(self, **keys: KeyLikeInt):
        """Update some dimensions scope.

        Only change specified dimensions.
        Acts on the parent scope of `scope` attribute.
        """
        keyring = self.keyring
        for dim, key in keys.items():
            keyring[dim] = key
        self.reset_scope(keyring)

    def update_scope_by_value(self, **keys: KeyLikeValue):
        """Update some dimensions scope by value.

        Only change specified dimensions.
        Acts on the parent scope of `scope` attribute.
        """
        keys_ = {}
        for dim, key in keys.items():
            keys_[dim] = KeyValue(key).apply(self.scope.dims[dim])
        self.update_scope(**keys_)

    def reset_scope(self, keyring: Keyring = None, **keys: KeyLikeInt):
        """Reset scope.

        Acts on the parent scope of `scope` attribute.
        """
        scope = self.db.get_subscope(self._target_scope, keyring,
                                     int2list=False, **keys)
        if scope.var != self.scope.var:
            self.update_variables(scope.var[:].tolist())
        self.scope = scope

    def update_variables(self, var: List[str]):
        """Update variables plotted."""
        if isinstance(self.var_idx, int):
            var_idx = [self.var_idx]
        else:
            var_idx = self.var_idx
        for i, v in zip(var_idx, var):
            self.axes[i] = v

    def reset_scope_by_value(self, **keys: KeyLikeValue):
        """Reset scope.

        Acts on the parent scope of `scope` attribute.
        """
        scope = self.db.get_subscope_by_value(self._target_scope,
                                              int2list=False, **keys)
        self.scope = scope

    def get_data(self) -> Array:
        """Retrieve data for plot.

        Either from `data` attribute if specified, or from database.
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
                             f" (is {dim}, expected {self.DIM})")

    def find_axes(self, axes: List[str] = None) -> List[str]:
        """Get list of axes.

        Find to what correspond the figures axes from plot object keyring.

        :param axes: [opt] Supply axes instead of guessing from keyring.
        """
        raise NotImplementedError()

    @classmethod
    def create(cls, db: 'DataPlot', ax: Axes,
               scope: Union[str, Scope] = 'loaded',
               axes: List[str] = None, data=None,
               kwargs: Dict[str, Any] = None,
               **keys: KeyLikeInt):
        """Create plot object."""
        scope_obj = db.get_subscope_by_value(scope, name='plotted',
                                             **keys, int2list=False)

        if scope_obj.var.size == 1:
            dims = db[scope_obj.var[0]].dims
            scope_obj.slice(**{d: 0 for d in db.dims if d not in dims},
                            int2list=False)

        if kwargs is None:
            kwargs = {}

        po = cls(db, ax, scope_obj, axes, data, **kwargs)

        po._target_scope = scope
        po.axes = po.find_axes(axes)

        if data is not None:
            if list(data.shape) != po.keyring.shape[:po.DIM]:
                raise IndexError("Data shape ({}) mismatch keyring shape ({})"
                                 .format(list(data.shape),
                                         po.keyring.shape[:po.DIM]))

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

        :param keys: [opt] Keys to change, as for `update_scope`.
        """
        self.update_scope(**keys)
        self.remove()
        self.create_plot()

    def set_limits(self):
        """Change axis limits to data."""
        self.ax.set_xlim(*self.get_limits(self.axes[0]))
        self.ax.set_ylim(*self.get_limits(self.axes[1]))

    def get_limits(self, name):
        """Retrieve limits for one of the axis.

        :param name: Coordinate or variable name.
        """
        if name in self.scope.coords:
            dim = self.scope[name]
            if isinstance(dim, Time):
                limits = dim.index2date([0, -1], pydate=True)
            else:
                limits = dim.get_limits()
        else:
            vmin = self.db.vi.get_attribute_default(name, 'vmin')
            vmax = self.db.vi.get_attribute_default(name, 'vmax')
            limits = vmin, vmax
        return limits

    def add_colorbar_axis(self, loc, size, pad, **kwargs):
        """Add axis for colorbar."""
        divider = make_axes_locatable(self.ax)
        self.cax = divider.append_axes(loc, size, pad, **kwargs)

    def add_colorbar(self, loc: str = "right",
                     size: float = .1,
                     pad: float = 0.,
                     **kwargs):
        """Add colorbar.

        :param loc: {'left', 'right', 'bottom', 'top'}
        """
        self.add_colorbar_axis(loc, size, pad, **kwargs)
        self.colorbar = self.ax.figure.colorbar(self.object, cax=self.cax, ax=self.ax)

    def _get_label(self, name: str, fullname: Union[bool, str],
                   units: Union[bool, str]):
        """Get label for axis.

        :param name: Coordinate or variable name.
        :param fullname: If True, use fullname if available.
            'fullname' attribute from a coordinate or the VI is used.
            If `fullname` is a string, use that attribute instead in the VI.
        :param units: If True, add units to label if available.
            'fullname' attribute from a coordinate or the VI is used.
            If `fullname` is a string, use that attribute instead in the VI.
        """
        if name in self.scope.coords:
            label = self.scope[name].fullname
            if not label or not fullname:
                label = name
            if units:
                c_units = self.scope[name].units
                if c_units:
                    label += ' [{}]'.format(c_units)
        else:
            attr = fullname if isinstance(fullname, str) else 'fullname'
            label = self.db.vi.get_attribute_default(name, attr)
            if label is None or not fullname:
                label = name
            if units:
                attr = units if isinstance(units, str) else 'units'
                v_units = self.db.vi.get_attribute_default(name, 'units')
                if v_units:
                    label += ' [{}]'.format(v_units)

        return label

    def set_labels(self, axes: Union[str, List[str]] = None,
                   fullname: Union[bool, str] = True,
                   units: Union[bool, str] = True):
        """Set axes labels.

        Set colorbar labels if present.

        :param axes: Axes to set labels to, can be 'x', 'y', 'colorbar' or 'cbar'.
            If None, all are set.
        :param fullname: If True, use fullname if available.
            'fullname' attribute from a coordinate or the VI is used.
            If `fullname` is a string, use that attribute instead in the VI.
        :param units: If True, add units to label if available.
            'fullname' attribute from a coordinate or the VI is used.
            If `fullname` is a string, use that attribute instead in the VI.
        """
        if axes is None:
            axes = ['X', 'Y']
            if self.colorbar is not None:
                axes.append('colorbar')
        elif not isinstance(axes, (list, tuple)):
            axes = [axes]
        for ax in axes:
            if ax.upper() == 'X':
                name = self.axes[0]
                f = self.ax.set_xlabel
            elif ax.upper() == 'Y':
                name = self.axes[1]
                f = self.ax.set_ylabel
            elif ax.upper() in ['COLORBAR', 'CBAR']:
                name = self.axes[-1]
                f = self.colorbar.set_label
            else:
                raise KeyError(f"Axis name not recognized ({ax}).")

            label = self._get_label(name, fullname, units)
            if label is not None:
                f(label)
