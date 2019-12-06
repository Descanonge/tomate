
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
For example, in a dataset of the sea surface temperature with an image
corresponding at a date per file, the latitude and longitude will be
'in' and the temperature 'shared'. There could also be more than one
date per file, for instance a file for each month with daily images.

The scanning is done independantly in each filegroup through the
:class:`CoordScan<data_loader.coord_scan.CoordScan>`, derived from
a :class:`Coord<data_loader.coord.Coord>`, or any of its subclass
(see :doc:`coord`).
The CoordScan object stores the values of the corresponding coordinate,
the in file index (noted in_idx), and for shared coordinates the
matches which are used to find the corresponding filenames.
All of those are indexed on the values, so when we ask for the
i_th value of a coordinate, we take the i_th matches to get the
corresponding filename.

In coordinates scan only one file, the first one found.
Shared coordinates scan all the files available.
The actual scanning (opening files) is done by user-defined
functions. These are set at runtime using the filegroups constructors.
There are two types of functions: `scan_filename` and `scan_in_file`.
The values and in file indices can also be set manually, in which case
the files won't be scanned, but the coordinates values will still
be checked for consistency with other filegroups.


Scanning in file
----------------

The function is set by
:func:`FGConstructor.set_scan_in_file_func<data_loader.constructor.FGConstructor.set_scan_in_file_func>`
. The function send to this receive a CoordScan object, a filename, and
values previously scanned in the filename (see below).
It must returns one or more values, and the corresponding index in the file.
If there is no index, the function should return `None`.

There are already existing function in the
:mod:`scan_library<data_loader.scan_library>` module.


Scanning filename: the pre-regex
--------------------------------

The filename can also be scanned, as sometimes it is the sole source
of information for a coordinate. This is done via a pre-regex, that
specify how the filename is constructed. This is useful to retrieve
information from the filename, but is also mandatory so that the
database know where are the files, and what part of the data they
contain.

More information on the pre-regex: :doc:`filegroup`.

Each scanned filename is matched again the regex constructed from
the pre-regex. The matches are temporarily stored in the matchers
of the right coordinates.
Again, the CoordScan calls a user-defined function set with
:func:`FGConstrictor.set_scan_filename_func<data_loader.constructor.FGConstructor.set_scan_filename_func>`
, with some functions already in :mod:`scan_library<data_loader.scan_library>`.
The function receives a Coordscan instance, and must returns one
or more values.
