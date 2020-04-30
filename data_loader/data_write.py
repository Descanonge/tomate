"""Write and read data objects from json files."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


# TODO: Coordinates values are not stored exactly (they pass as text)

from importlib import import_module
import logging
import json


import numpy as np

from data_loader import VariablesInfo, Constructor


log = logging.getLogger(__name__)
__all__ = ['write', 'read']


def serialize_type(tp):
    top = {"__module__": tp.__module__,
           "__name__": tp.__name__}
    return top

def read_type(j_tp):
    module = import_module(j_tp['__module__'])
    tp = getattr(module, j_tp['__name__'])
    return tp

def default(obj):
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
        log.warning("'%s' (%s) obj not serializable, replaced by None.", s, type(obj))
        obj = None

    return obj


def write(filename, cstr):
    j_cstr = serialize_cstr(cstr)
    with open(filename, 'w') as f:
        json.dump({'cstr': j_cstr},
                  f, indent=4, default=default)

def read(filename):
    with open(filename, 'r') as f:
        d = json.load(f)
    cstr = read_cstr(d['cstr'])
    return cstr

def serialize_cstr(cstr):
    j_bases = [serialize_type(cls) for cls in cstr.dt_types]
    j_acs = serialize_type(cstr.acs)
    j_coords = {name: serialize_coord(c) for name, c in cstr.coords.items()}
    j_vi = serialize_vi(cstr.vi)
    j_filegroups = [serialize_filegroup(fg) for fg in cstr.filegroups]

    top = {"bases": j_bases,
           "acs": j_acs,
           "root": cstr.root,
           "coords": j_coords,
           "vi": j_vi,
           "filegroups": j_filegroups}
    return top

# FIXME: coord selection
def read_cstr(j_cstr):
    root = j_cstr["root"]
    coords = [read_coord(j_c) for j_c in j_cstr["coords"].values()]
    cstr = Constructor(root, coords)

    bases = [read_type(j_tp) for j_tp in j_cstr["bases"]]
    acs = read_type(j_cstr["acs"])
    cstr.set_data_types(bases, acs)

    cstr.vi = read_vi(j_cstr["vi"])

    for j_fg in j_cstr["filegroups"]:
        add_filegroup(cstr, j_fg)

    return cstr

def add_filegroup(cstr, j_fg):
    tp = read_type(j_fg["class"])
    root = j_fg["root"]
    contains = j_fg["contains"]
    coords = [[cstr.coords[name], c["shared"], c["name"]]
              for name, c in j_fg["cs"].items()]
    variables_shared = j_fg["cs"]["var"]["shared"]
    name = j_fg["name"]
    # TODO: kwargs in FG creation missing

    cstr.add_filegroup(tp, coords, name=name, root=root,
                       variables_shared=variables_shared)
    cstr.set_fg_regex(j_fg["pregex"])
    fg = cstr.current_fg
    fg.segments = j_fg["segments"]

    for tp, [j_func, scanned, kwargs] in j_fg["scan_attr"].items():
        fg.scan_attr[tp] = [read_type(j_func), scanned, kwargs]

    for name, j_cs in j_fg["cs"].items():
        cs = fg.cs[name]

        for tp, j_scan in j_cs["scan"].items():
            func = None if j_scan['func'] is None else read_type(j_scan['func'])
            cs.scan[tp] = [j_scan['elts'], func, j_scan['kwargs']]
        cs.scan_attributes_func = read_type(j_cs["scan_attributes_func"])

        cs.values = j_cs["values"][0]
        cs.in_idx = j_cs["in_idx"][0]
        if cs.shared:
            cs.matches = j_cs["matches"]
        cs.set_values()
        cs.update_values(cs.values)

        cs.force_idx_descending = j_cs["force_idx_descending"]


def serialize_filegroup(fg):
    top = {"name": fg.name,
           "root": fg.root,
           "contains": fg.variables,
           "class": serialize_type(fg.__class__),
           "segments": fg.segments,
           "pregex": fg.pregex}
    scan = {}
    for tp, [func, scanned, kwargs] in fg.scan_attr.items():
        scan[tp] = [serialize_type(func), scanned, kwargs]
        # TODO: kwargs might not be adapted
    top["scan_attr"] = scan

    top["cs"] = {name: serialize_coord_scan(cs)
                 for name, cs in fg.cs.items()}
    return top


def serialize_coord_scan(cs):
    top = {"name": cs.name,
           "base": serialize_type(type(cs)),

           "shared": cs.shared,
           "force_idx_descending": cs.force_idx_descending}

    scan = {}
    for tp, [func, elts, kwargs] in cs.scan.items():
        j_func = None if func is None else serialize_type(func)
        scan[tp] = {'elts': elts,
                    'func': j_func,
                    'kwargs': kwargs}
        # TODO: kwargs might not be adapted
    top['scan'] = scan
    top['scan_attributes_func'] = serialize_type(cs.scan_attributes_func)

    top["values"] = cs[:].tolist(),
    top["in_idx"] = cs.in_idx.tolist(),
    if cs.shared:
        top["matches"] = cs.matches.tolist()


    return top


def serialize_vi(vi):
    top = {"attrs" : vi._attrs,
           "infos": vi._infos}
    return top

def read_vi(j_vi):
    infos = j_vi['infos']
    attrs = j_vi['attrs']
    vi = VariablesInfo(None, **infos)
    for attr, values in attrs.items():
        vi.set_attr_variables(attr, **values)
    return vi


def serialize_coord(coord, values=False):
    top = {"name": coord.name,
           "class": serialize_type(coord.__class__),
           "units": coord.units,
           "fullname": coord.fullname}
    if values:
        top["values"] = coord[:].tolist()
    else:
        top["values"] = None
    return top

def read_coord(j_c):
    cls = read_type(j_c['class'])
    coord = cls(j_c['name'], j_c['values'], j_c['units'], j_c['fullname'])
    return coord
