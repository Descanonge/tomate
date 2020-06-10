"""Write and read data objects from json files."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


# TODO: Coordinates values are not stored exactly (they pass as text)

from importlib import import_module
import logging
import json


import numpy as np

from tomate import VariablesInfo, Constructor


log = logging.getLogger(__name__)


def serialize_type(tp):
    top = {"__module__": tp.__module__,
           "__name__": tp.__name__}
    return top


def read_type(j_tp):
    # TODO: add try except. We cannot except to be able to import anything
    module = import_module(j_tp['__module__'])
    tp = getattr(module, j_tp['__name__'])
    return tp


def default(obj):
    try:
        s = str(obj)
    except TypeError:
        s = None

    # TODO: slices

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


def write(filename, db):
    j_db = serialize_db(db)
    with open(filename, 'w') as f:
        json.dump({'db': j_db},
                  f, indent=4, default=default)


def recreate_cstr(filename):
    with open(filename, 'r') as f:
        d = json.load(f)
    cstr = read_cstr(d['db'])
    return cstr


def serialize_db(db):
    j_bases = [serialize_type(cls) for cls in db.__class__.__bases__]
    j_acs = serialize_type(db.acs)
    j_dims = {name: serialize_coord(c) for name, c in db.avail.dims.items()}
    j_vi = serialize_vi(db.vi)
    j_filegroups = [serialize_filegroup(fg) for fg in db.filegroups]

    j_db = {"bases": j_bases,
            "acs": j_acs,
            "root": db.root,
            "dims": j_dims,
            "vi": j_vi,
            "filegroups": j_filegroups}
    return j_db


def read_cstr(j_db):
    root = j_db["root"]
    dims = [read_coord(j_c) for j_c in j_db["dims"].values()]
    cstr = Constructor(root, dims)

    bases = [read_type(j_tp) for j_tp in j_db["bases"]]
    acs = read_type(j_db["acs"])
    cstr.set_data_types(bases, acs)

    cstr.vi = read_vi(j_db["vi"])

    for j_fg in j_db["filegroups"]:
        add_filegroup(cstr, j_fg)

    return cstr


def add_filegroup(cstr, j_fg):
    tp = read_type(j_fg["class"])
    root = j_fg["root"]
    coords = [[cstr.dims[name], c["shared"], c["name"]]
              for name, c in j_fg["cs"].items()]
    name = j_fg["name"]
    # TODO: kwargs in FG creation missing

    cstr.add_filegroup(tp, coords, name=name, root=root)
    cstr.set_fg_regex(j_fg["pregex"])
    fg = cstr.current_fg
    fg.segments = j_fg["segments"]

    for tp, [j_func, scanned, kwargs] in j_fg["scan_attr"].items():
        fg.scan_attr[tp] = [read_type(j_func), scanned, kwargs]

    for name, j_cs in j_fg["cs"].items():
        cs = fg.cs[name]

        for tp, j_scan in j_cs["scan"].items():
            func = None if j_scan['func'] is None else read_type(j_scan['func'])
            cs.scan[tp] = [func, j_scan['elts'], j_scan['kwargs']]
        cs.scan_attributes_func = read_type(j_cs["scan_attributes_func"])

        cs.values = j_cs["values"]
        cs.in_idx = j_cs["in_idx"]
        if cs.shared:
            cs.matches = j_cs["matches"]
        cs.set_values()
        if cs.is_to_check() or cs.name == 'var':
            cs.update_values(cs.values)

        cs.change_units_custom = (None if j_cs["change_units_custom"] is None else
                                  read_type(j_cs["change_units_custom"]))
        cs.find_contained_kwargs = j_cs["find_contained_kwargs"]

        cs.force_idx_descending = j_cs["force_idx_descending"]


def serialize_filegroup(fg):
    top = {"name": fg.name,
           "root": fg.root,
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

           "change_units_custom": (None if cs.change_units_custom is None
                                   else serialize_type(cs.change_units_custom)),
           "find_contained_kwargs": cs.find_contained_kwargs,

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

    if cs.size is None:
        top["values"] = []
        top["in_idx"] = []
    else:
        top["values"] = cs[:].tolist()
        top["in_idx"] = cs.in_idx.tolist()
    if cs.shared:
        top["matches"] = cs.matches.tolist()

    return top


def serialize_vi(vi):
    top = {"attrs": vi._attrs,
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
    coord = cls(name=j_c['name'], array=j_c['values'],
                units=j_c['units'], fullname=j_c['fullname'])
    return coord
