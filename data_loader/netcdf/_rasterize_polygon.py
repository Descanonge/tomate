"""Transform a shapely Polygon into a raster.

From github.com/perrette
http://gist.github.com/perrette/a78f99b76aed54b6babf3597e0b331f8
"""

import numpy as np

from shapely.geometry import Point
from shapely.geometry.polygon import Polygon

import matplotlib.path as mplp


def outline_to_mask(line, x, y):
    """Create mask from outline contour.

    Parameters
    ----------
    line: array-like (N, 2)
    x, y: 1-D grid coordinates (input for meshgrid)

    Returns
    -------
    mask : 2-D boolean array (True inside)

    Examples
    --------
    >>> from shapely.geometry import Point
    >>> poly = Point(0,0).buffer(1)
    >>> x = np.linspace(-5,5,100)
    >>> y = np.linspace(-5,5,100)
    >>> mask = outline_to_mask(poly.boundary, x, y)

    """
    mpath = mplp.Path(line)
    X, Y = np.meshgrid(x, y)
    points = np.array((X.flatten(), Y.flatten())).T
    mask = mpath.contains_points(points).reshape(X.shape)
    return mask


def _grid_bbox(x, y):
    dx = dy = 0
    return x[0]-dx/2, x[-1]+dx/2, y[0]-dy/2, y[-1]+dy/2


def _bbox_to_rect(bbox):
    l, r, b, t = bbox
    return Polygon([(l, b), (r, b), (r, t), (l, t)])


def shp_mask(shp, x, y, m=None):
    """Create raster mask from shapely polygon.

    Use recursive sub-division of space and shapely contains method
    to create a raster mask on a regular grid.

    Parameters
    ----------
    shp : shapely's Polygon (or whatever with a "contains" method and
     intersects method) or a numpy array of points
    x, y : 1-D numpy arrays defining a regular grid
    m : mask to fill, optional (will be created otherwise)

    Returns
    -------
    m : boolean 2-D array, True inside shape.

    Examples
    --------
    >>> from shapely.geometry import Point
    >>> poly = Point(0,0).buffer(1)
    >>> x = np.linspace(-5,5,100)
    >>> y = np.linspace(-5,5,100)
    >>> mask = shp_mask(poly, x, y)

    """

    if isinstance(shp, (tuple, list, np.ndarray)):
        shp = Polygon(shp)

    rect = _bbox_to_rect(_grid_bbox(x, y))

    if m is None:
        m = np.zeros((y.size, x.size), dtype=bool)

    if not shp.intersects(rect):
        m[:] = False
    elif shp.contains(rect):
        m[:] = True

    else:
        i, j = m.shape

        if i == 1 and j == 1:
            m[:] = shp.contains(Point(x[0], y[0]))

        elif i == 1:
            m[:, :j//2] = shp_mask(shp, x[:j//2], y, m[:, :j//2])
            m[:, j//2:] = shp_mask(shp, x[j//2:], y, m[:, j//2:])

        elif j == 1:
            m[:i//2] = shp_mask(shp, x, y[:i//2], m[:i//2])
            m[i//2:] = shp_mask(shp, x, y[i//2:], m[i//2:])

        else:
            m[:i//2, :j//2] = shp_mask(shp,
                                       x[:j//2], y[:i//2], m[:i//2, :j//2])
            m[:i//2, j//2:] = shp_mask(shp,
                                       x[j//2:], y[:i//2], m[:i//2, j//2:])
            m[i//2:, :j//2] = shp_mask(shp,
                                       x[:j//2], y[i//2:], m[i//2:, :j//2])
            m[i//2:, j//2:] = shp_mask(shp,
                                       x[j//2:], y[i//2:], m[i//2:, j//2:])

    return m
