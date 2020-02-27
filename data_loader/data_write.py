"""Write and read data objects from json files."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK

from importlib import import_module
import logging
import json


import numpy as np

from data_loader import VariablesInfo
from data_loader.constructor import create_data_class


log = logging.getLogger(__name__)
__all__ = ['write', 'read']


def write(data, filename):
    """."""
    with open(filename, 'w') as f:
        json.dump(serialize_data(data), f, indent=4, default=default)


def read(filename):
    """."""
    with open(filename, 'r') as f:
        d = json.load(f)
    dt = read_data(d['data'])
    return dt


def serialize_data(data):
    """."""
    bases = [serialize_type(cls) for cls in data.__class__.__bases__]
    acs = serialize_type(data.acs.__class__)
    vi = serialize_vi(data.vi)
    filegroups = [serialize_filegroup(fg) for fg in data.filegroups]
    coords = [serialize_coord(data.avail.coords[name]) for name in data.coords_name]

    top = {"bases": bases,
           "root": data.root,
           "acs": acs,
           "vi": vi,
           "coords": coords,
           "filegroups": filegroups}
    return {"data": top}


def read_data(j_data):
    """."""
    types = read_data_types(j_data['bases'])
    acs = read_type(j_data['acs'])()
    cls = create_data_class(types, acs)

    root = j_data['root']
    coords = [read_coord(d) for d in j_data['coords']]

    vi = read_vi(j_data['vi'])
    filegroups = [read_filegroup(fg, coords, vi) for fg in j_data['filegroups']]

    dt = cls(root, filegroups, vi, *coords)

    return dt

def read_data_types(j_types):
    """."""
    types = []
    for j_type in j_types:
        mod = import_module(j_type['__module__'])
        types.append(getattr(mod, j_type['__name__']))
    return types
   

def serialize_filegroup(fg):
    """."""
    cs = [serialize_coord_scan(c) for c in fg.cs.values()]
    top = {"contains": fg.contains,
           "class": serialize_type(fg.__class__),
           "root": fg.root,
           "pregex": fg.pregex,
           "regex": fg.regex,
           "segments": fg.segments,
           "scan_attr": fg.scan_attr,
           "cs" : cs}
    return top


def read_filegroup(j_fg, coords, vi):
    """."""
    root = j_fg['root']
    contains = j_fg['contains']
    cls = read_type(j_fg['class'])

    coords_d = {c.name: c for c in coords}
    coords_fg = [[coords_d[c['name']], c['shared']]
                 for c in j_fg['cs']]

    fg = cls(root, contains, None, coords_fg, vi)

    for j_cs in j_fg['cs']:
        name = j_cs['name']
        in_idx = np.array(j_cs['in_idx'])
        values = np.array(j_cs['values'])
        scan_filename_kwargs = j_cs['scan_filename_kwargs']
        scan_in_file_kwargs = j_cs['scan_in_file_kwargs']

        cs = fg.cs[name]
        cs.in_idx = in_idx
        cs.set_values(values)
        cs.assign_values()

    return fg


def serialize_coord_scan(cs):
    """."""
    tp = cs.__class__
    shared = 'Shared' in tp.__name__
    base = tp.__bases__[1].__bases__[1]

    top = {"name": cs.name,
           "shared": shared,
           "base": serialize_type(tp),
           "values": cs[:].tolist(),
           "in_idx": cs.in_idx.tolist(),
           "scan": list(cs.scan),
           "scanned": cs.scanned,
           "scan_filename_kwargs": cs.scan_filename_kwargs,
           "scan_in_file_kwargs": cs.scan_in_file_kwargs}

    # TODO: write used functions

    if shared:
        top["matches"] = cs.matches.tolist()

    return top


def read_coord_scan(j_cs, coord):
    """."""
    assert j_cs['name'] == coord.name, "CS not matching Coord."
    shared = j_cs['shared']
    return [coord, shared]


def serialize_coord(coord):
    """."""
    top = {"name": coord.name,
           "class": serialize_type(coord.__class__),
           "units": coord.units,
           "name_alt": coord.name_alt,
           "fullname": coord.fullname,
           "values": coord[:].tolist()}
    return top


def read_coord(j_c):
    """."""
    cls = read_type(j_c['class'])
    coord = cls(j_c['name'], j_c['values'], j_c['units'],
                j_c['name_alt'], j_c['fullname'])
    return coord


def serialize_vi(vi):
    """."""
    top = {"variables": vi.var,
           "attrs" : vi._attrs,
           "infos": vi._infos}
    return top


def read_vi(j_vi):
    """."""
    variables = j_vi['variables']
    infos = j_vi['infos']
    attrs = j_vi['attrs']
    vi = VariablesInfo(variables, None, **infos)
    for attr, values in attrs.items():
        vi.add_attr(attr, values)

    return vi


def serialize_type(tp):
    """."""
    top = {"__module__": tp.__module__,
           "__name__": tp.__name__}
    return top


def read_type(j_tp):
    """."""
    module = import_module(j_tp['__module__'])
    tp = getattr(module, j_tp['__name__'])
    return tp


def default(obj):
    """."""
    try:
        s = str(obj)
    except TypeError:
        s = None

    if isinstance(obj, np.ndarray):
        obj = obj.tolist()
        log.warning("'%s' array converted to list.", s)
    elif isinstance(obj, (np.integer)):
        obj = int(obj)
    elif isinstance(obj, (np.float)):
        obj = float(obj)
    else:
        obj = None
        log.warning("'%s' obj not serializable, replaced by None.", s)

    return obj
