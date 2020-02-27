
.. currentmodule :: data_loader

Scanning
========

At its creation, the database object look into the available
files in a process called scanning.
It looks inside the files and at their filenames to find
how the data is arranged.
It can find the values of the coordinates, and their placement
in the files, for instance if the latitudinal dimension is reversed.

Some dimensions are found entirely in the files: they are 'in',
others can be scattered accross different files: they are 'shared'.
In-coordinates are also assumed to be arranged in the same way for all files
(same range, same indexing). If this is not the case, the coordinate should
be marked as shared.
For example, in a dataset of the sea surface temperature with an image per date
per file, the latitude and longitude will be 'in' and the temperature 'shared'.
There could also be more than one date per file, for instance a file for each
month with daily images.

The scanning is done independantly in each filegroup through the
:class:`CoordScan<filegroup.coord_scan.CoordScan>` object, dynamically derived
from a :class:`Coord<coordinates.coord.Coord>`, or any of its subclass.

The CoordScan object stores the values of its parent coordinate,
the in-file indices (noted `in_idx`), and for shared coordinates the
part of the filename that were found against matchers from the regex.
All those variables are indexed on the coordinate values, so when we ask for the
i_th value of a coordinate, we take the i_th series of matches to get the
corresponding filename, and the i_th in-file index to know where to look in that
file.

The fact that everything is indexed on coordinates values, means that
coordinates scanned from files will always have values in growing order.
If needed, the data will be reversed to accomodate (see
:ref:`Reversing dimensions`).

In-coordinates scan only one file, the first one found.
Shared coordinates scan all the files available.
The actual scanning (opening files) is done by user-defined
functions. These are set at runtime using the filegroups constructors.
There are two types of functions: `scan_filename` and `scan_in_file``.
The values and in file indices can also be set manually, in which case
the files won't be scanned, but the coordinates values will still
be checked for consistency with other filegroups.

Coordinate attributes, variables attributes, and general information on
the data can all be retrieved from files.
Functions to accomplish this are set with
:func:`constructor.Constructor.set_scan_coords_attributes_func`,
:func:`constructor.Constructor.set_scan_variables_attributes_func`, and
:func:`constructor.Constructor.set_scan_infos_func`, respectively.
See their docstrings for more information.
Currently, the only attributes that can be applied this way for coordinates
is their units.


Reversing dimensions
--------------------

When dealing with images, it is not always easy to know how the image
is indexed, ie where the `[0, 0]` pixel is located.
As the CoordScan stores the in file index for each value it is easy
to know if a dimension can be considered 'index descending', meaning
the values of the coordinate are descending when the in-file index increases.
In that case, the CoordScan instance will return True when asked
`is_idx_descending()`, and when loading data the in file key for
this dimension will be reversed.

If no information on the in-file index can be found inside the file,
the `in_idx` attribute CoordScan will be set to a list of `None`.
The index descending property can still be set manually by calling
:func:`Constructor.set_coord_descending(coord_name)<constructor.Constructor.set_coord_descending>`
on the filegroup constructor.

This only works for 'in' coordinates.
For even more control on how the data is loaded, one should use
the post load function of the :doc:`data object<data>`.


Scanning in file
----------------

The scanning function is set by
:func:`Constructor.set_scan_in_file_func<constructor.Constructor.set_scan_in_file_func>`
(a wrapper around
:func:`filegroup.coord_scan.CoordScan.set_scan_in_file_func`).
The function should receive a CoordScan object, a filename, and
values previously scanned in the filename (see below).
It must returns one or more values, and the corresponding indices in the file.
If there is no index, the function should return `None`.

There are already existing functions in the
:mod:`data_loader.scan_library` module.


Scanning filename: the pre-regex
--------------------------------

The filename can also be scanned, as sometimes it is the sole source
of information for a coordinate. This is done via a pre-regex, that
specifies how the filename is constructed. This is useful to retrieve
information from the filename, but is also mandatory so that the
database know where are the files, and what part of the data they
contain.

More information on the pre-regex: :doc:`filegroup`.

Each scanned filename is matched again the regex constructed from
the pre-regex. The matches are temporarily stored in the matchers
of the corresponding coordinates.
Again, the CoordScan calls a user-defined function set with
:func:`Constructor.set_scan_filename_func<constructor.Constructor.set_scan_filename_func>`
(a wrapper around
:func:`filegroup.coord_scan.CoordScan.set_scan_filename_func` ),
eventually with functions already in :mod:`scan_library<data_loader.scan_library>`.
The function receives a Coordscan instance, and must returns one
or more values.
