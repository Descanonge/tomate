
.. currentmodule :: data_loader

Scanning
========

At its creation, the database object look into the available
files on disk in a process called scanning.
It looks inside the files and at their filenames to find
how the data is arranged.
It can find the values of the coordinates, and their placement
in the files, for instance if the latitudinal dimension is reversed.

All of the scanning is coordinate specific and thus mainly handled
by :class:`CoordScan<filegroup.coord_scan.CoordScan>`.
The filegroup orchestrate the scanning, and the constructor makes some
additional checks.
The filegroup also eventually scans for general attributes.


Some generalities
-----------------

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

Some coordinates might not be represented inside the file (for instance
the file contains one step of a shared coordinate).
In that case, the in-file index should be `None`.
This is then handled appropriately by the filegroup loading methods.

In-coordinates scan only one file, the first one found.
Shared coordinates scan all the files available.
The actual scanning is done by user-defined functions
(some functions are provided in the
:mod:`scan_library<data_loader.scan_library>` module).
These are set at runtime using the constructor.
The different flavors of scanning (attributes, in-file, filename)
are done in the order they were specified by the user.
The coordinates will be scanned in the order they were specified
when adding a filegroup.
This is useful if the scanning of some values require to fetch
some attributes in the file for instance.

There are two types of functions: `scan_filename` and `scan_in_file`.
See the two sections below for more information.
The values and in file indices can also be set manually, in which case
the files won't be scanned, but the coordinates values will still
be checked for consistency with other filegroups.
The filenames will still be scanned, but only to associate found matches
with the values and in-indices manually set
(see `examples/variables_scanning.py` for more details).

Coordinate attributes, variables attributes, and general information on
the data can all be retrieved from files.
Functions to accomplish this are set with
:func:`constructor.Constructor.set_scan_coords_attributes` and
:func:`constructor.Constructor.set_scan_general_attributes`.
See their docstrings for more information.
The coordinates attributes found by the functions, are send to the
parent coordinate :func:`Coord.set_attr<coordinates.coord.Coord.set_attr>`
method.


Variables Coordinates
---------------------

Variables are treated as coordinates when scanning, with some specificities.

Variables are considered 'in' by default. They can be set to shared
when creating the filegroup.

Variables are normally added to the constructor using
:func:`add_variable<constructor.Constructor.add_variable>`, along
with attributes for the :doc:`VI<variables_info>`, but they can
also be scanned.
The CoordScan for variables is special in that it receives default in-file
indices.
Values should always be the variables names. The default values for in-file
indices are also the variables names.
Thoses default values are reset if the user specifies manually those with
:func:`Constructor.set_variables_infile<constructor.Constructor.set_variables_infile>`,
or using a scan function as with any other coordinate.

Contrary to other CoordScan, the values are not sorted after being scanned.

Variables attributes can be scanned in files as with other coordinates.
The attributes found are added to the VI.
Note that it is currently not possible to let the scanning find all the
variables, *and* retrieve variable attributes.


Reversing dimensions
--------------------

When dealing with images, it is not always easy to know how the image
is indexed, *ie* where the `[0, 0]` pixel is located.
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
the :ref:`Post loading function` of the data object.


Scanning in file
----------------

The scanning function is set by
:func:`Constructor.set_scan_in_file<constructor.Constructor.set_scan_in_file>`
(a wrapper around
:func:`filegroup.coord_scan.CoordScan.set_scan_in_file_func`).
The function should receive a CoordScan object, a file object, and
values eventually scanned from the filename if the filename scanning was
done before-hand.
It must returns one or more values, and the corresponding indices in the file.

The file object is a handle for whatever file format is needed.
It is returned by the Filegroup
:func:`open_file<filegroup.filegroup_scan.FilegroupScan.open_file>`
method.
All exception handling (and closing the file appropriately) is done
by the package.


Scanning filename: the pre-regex
--------------------------------

The filename can also be scanned, as sometimes it is the sole source
of information for a coordinate.
This is done via a pre-regex, a regular expression with added features
that specifies how the filename is constructed.
This is useful to retrieve information from the filename, but is also mandatory
so that the database know where are the files, and what part of the data they
contain.

Any regex can be used in the pre-regex, however, it will be replaced
by its match as found in the first file and then considered constant.
For example, if we have daily files 'sst_2003-01-01.nc' with the
date changing for each file. We could use the regex `sst_.*\.nc`, which
would match correctly all files, but the program would then consider that
*all* filenames are 'sst_2003-01-01.nc'

Instead, we must specify what part of the filename varies, and along
which dimension / coordinate.
To this end, we use :class:`matchers<filegroup.coord_scan.Matcher>`.
This is a part of the pre-regex, enclosed in parenthesis and preceded
by a `%`. It specifies the coordinate name and the element of the coordinate.

Re-using the example above, we would use three matchers - one for each
element of the date - for the time coordinate::

  sst_%(time:Y)-%(time:mm)-%(time:dd)

The first matcher corresponds to the year. The element name ('Y'), is
used later to extract information from the filename. It is also
used to construct a proper regex, by indicating that we expect four
digits there.

Hard coded elements are available:

+----------------+-------------------------+--------------------------+
|  Element name  |          Regex          |                          |
+----------------+-------------------------+--------------------------+
|      idx       |          \\d*           |          Index           |
+----------------+-------------------------+--------------------------+
|      text      |        [a-zA-Z]*        |         Letters          |
+----------------+-------------------------+--------------------------+
|      char      |          \\S*           |        Character         |
+----------------+-------------------------+--------------------------+
|        x       |    \d\d\d\d\d\d\d\d     |     Date (YYYYMMDD)      |
+----------------+-------------------------+--------------------------+
|        Y       |      \\d\\d\\d\\d       |       Year (YYYY)        |
+----------------+-------------------------+--------------------------+
|       mm       |         \\d?\\d         |       Month ([M]M)       |
+----------------+-------------------------+--------------------------+
|       dd       |         \\d?\\d         |    Day of month ([D]D)   |
+----------------+-------------------------+--------------------------+
|       doy      |       \\d?\\d?\\d       |   Day of year ([DD]D)    |
+----------------+-------------------------+--------------------------+
|        M       |        [a-zA-Z]*        |        Month name        |
+----------------+-------------------------+--------------------------+


All the use cases are not covered, and one might want to use a specific
regex in place of the matcher. One could modify the definition of the
Matcher class, or use a custom regex as so::

  sst_%(time:Y:custom=\d\d\d\d:)-%(time:mm)-%(time:dd)

**The custom regex must be terminated with a colon `:`**.

The filename can comport varying part which are not detrimental to the
extraction of coordinate values. They still have to be specified, but one
can append the 'dummy' keyword to the matcher to make clear that this
information is to be discarded. This is usefull for instance when dealing
with filenames that specify the averaging boundaries::

  sst_%(time:Y)-%(time:Y:dummy)
  sst_%(time:Y)-%(time:Y:custom=\d\d\d\d:dummy)

More use cases are presented in the :doc:`tutorial` and examples.

Each scanned filename is matched again the regex constructed from
the pre-regex. The matches are temporarily stored in the matchers
of the corresponding coordinates.
Again, the CoordScan calls a user-defined function set with
:func:`Constructor.set_scan_filename<constructor.Constructor.set_scan_filename>`
(a wrapper around
:func:`filegroup.coord_scan.CoordScan.set_scan_filename_func` ),
and functions are provided in :mod:`scan_library<data_loader.scan_library>`.
The function receives a Coordscan instance, and values eventually scanned from
inside the same file if the in-file scanning was done before-hand.
It must returns one or more values, and eventually in-file indices.
