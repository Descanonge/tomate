"""Abstract object containing information about plots."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import Any, Dict, List, Union, TYPE_CHECKING

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from mpl_toolkits.axes_grid1 import make_axes_locatable

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
    :attr ax: matplotlib.axes.Axes:
    :attr scope: Scope: Scope of plotted data.
        If data is to be fetched from database, ought to be a
        child of its loaded scope, its parent keyring should
        have the correct dimension.
    :attr object: Any: Object returned by matplotlib.
    :attr data: Optional[Array]: If not None, data to use
        (instead of fetching it from database).
    :attr axes: List[str]: Dimensions and variables name, in order of axes
        (x, y, [z], [color]).
    :attr kwargs: Dict[Any]: Keyword arguments to use for creating plot.
    :attr cax: matplotlib.axes.Axes: Colorbar axis.
    :attr colorbar: matplotlib.colorbar.Colorbar: Colorbar object.
    """

    DIM = 0  #: Dimension of the data to plot.

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
        self.cax = None
        self.colorbar = None

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
        self.ax.set_xlim(*self.get_limits(self.axes[0]))
        self.ax.set_ylim(*self.get_limits(self.axes[1]))

    def get_limits(self, name):
        """Retrieve limits for one of the axis.

        :param name: Coordinate or variable name.
        """
        if name in self.scope.coords:
            limits = self.scope[name].get_limits()
        else:
            vmin = self.db.vi.get_attr_safe(name, 'vmin')
            vmax = self.db.vi.get_attr_safe(name, 'vmax')
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
        self.colorbar = plt.colorbar(self.object, cax=self.cax, ax=self.ax)

    def _get_label(self, name: str,
                   fullname: Union[bool, str], units: Union[bool, str]):
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
            label = self.db.vi.get_attr_safe(attr, name)
            if label is None or not fullname:
                label = name
            if units:
                attr = units if isinstance(units, str) else 'units'
                v_units = self.db.vi.get_attr_safe('units', name)
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
