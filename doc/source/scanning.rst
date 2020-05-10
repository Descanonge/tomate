
.. currentmodule :: data_loader

Scanning
========

At its creation, the database object look into the available
files on disk in a process called scanning.
It looks inside the files and at their filenames to find
how the data is arranged.
It can find the values of the coordinates, and their placement
in the files.

Most of the scanning is coordinate specific and thus mainly handled
by :class:`CoordScan<filegroup.coord_scan.CoordScan>`.
The filegroup orchestrate the scanning, and the constructor compiles
information from all filegroups.
The filegroup also eventually scans for variable specific, and
general information on the data.


Some generalities
-----------------

Some dimensions are found entirely in each file: they are 'in',
others can be scattered accross different files: they are 'shared'.
In-coordinates are also assumed to be arranged in the same way for all files
(same values, same indexing). If this is not the case, the coordinate should
be marked as shared. Keep in mind all coordinates are independent.
For example, in a dataset of the sea surface temperature with an image per date
per file, the latitude and longitude will be 'in' and the temperature 'shared'.
There could also be more than one date per file, for instance a file for each
month with daily images.

The scanning is done independantly in each filegroup through the
:class:`CoordScan<filegroup.coord_scan.CoordScan>` object
(often abbrievated CS), dynamically derived
from a :class:`Coord<coordinates.coord.Coord>`, or any of its subclass.
The CS must find 2 to 3 things: the coordinates values, the index in the
file for that value, and if the CS is shared, the file that contains this value.
All those variables are indexed on the coordinate values, so when we ask for the
i_th value of a coordinate, we take the i_th file, and the i_th
in-file index to know where to look in that file.
The fact that everything is indexed on coordinates values, means that
coordinates scanned from files will always have values in growing order.

No full filenames are stored. Rather, the matches from the pre-regex
corresponding to that coordinate are kept for each coordinate value.
This avoid storing an excessive number of long filenames, especially if there
are multiple shared coordinates.
With the matches from all the shared coordinates, we can reconstruct the
filename, by replacing the matchers in the pre-regex.
This add a limitation with multiple shared coordinates: the matches must also
be independent accross coordinates.

Some dimensions might not be represented inside the file, for instance
in the previous example files might not contain a time dimension.
In that case, the in-file index should be `None`.
This is then handled appropriately by the filegroup loading methods.

In-coordinates scan only one file, the first one found.
Shared coordinates scan all the files available.
The scanning is done by user-defined functions. Those functions can
either look inside a file, or at its filename.
Only one function can be called for each type of scanning (in-file and
filename).
The functions are launched in the same order they were specified by the user
to the filegroup.
Each can extract coordinates values and/or in-file indices.
The values they extract can be passed from one to another.
So, for instance with monthly files, one could first find the year and month
in the filename, and the day of the month in the file.
It would combine both to create the whole date. In-file indices should
of course be recovered from inside the file.
More details in following sections.

This whole process can be overlooked by setting manually the values and
in-file indices.
For shared coordinates, the scanning of values should still be happening,
as each filename must be associated with one or more values.
In that case, the value found by scanning is expected to be present in
the values set manually. The in-file index set by the user is left untouched.

Multiple filegroups
-------------------

One can deals with multiple filegroups.
When all filegroups have finished scanning, the constructor will compile
found values. This will dictate the range of the 'available' scope.
By default, only coordinates points common to all filegroups are taken.
The variables dimension is an exception to this.
If in some filegroup a coordinate must be reduced a warning will be emitted.
Duplicate coordinates points (variables and
coordinates values are identical in two different filegroups), are not
supported.
To avoid those, one can select parts of the CS to take in each filegroup,
either by index or value (:func:`constructor.Constructor.set_coord_selection`).

By setting the flag :attr:`constructor.Constructor.allow_advanced` to `True`,
one unlocks some possibilities.
This allows to retain all found values, not only values common accross
filegroups.
Duplicates are still not supported.
This makes possible some nice features, like having a variable split
accross two filegroups. For instance multiple filegroups containing
different spatial or temporal ranges of a same variable.

However one must be careful. This allows to have multiple coordinates
grid at the same time, which could be unwanted.
It also allows non-convex data grids. A variable could be available
at a location where other are not for instance. By loading all variables
at this location, parts of the data array would be allocated but left
untouched, without warnings being emitted.
To use with some caution.


Attributes scanning
-------------------

Coordinate attributes, variables attributes, and general information on
the data can all be retrieved from files.
Functions to accomplish this are set with
:func:`constructor.Constructor.set_scan_coords_attributes` and
:func:`constructor.Constructor.set_scan_general_attributes`.
See their docstrings for more information.
The coordinates attributes found by the functions, are send to the
parent coordinate :func:`Coord.set_attr<coordinates.coord.Coord.set_attr>`
method.

One can also scan coordinate attributes in the first file found,
such as units, or dimension fullname. This is always done first.


Units conversion
----------------

The coordinates values found by scanning might not have the desired units.
One can rely one the :func:`coordinates.coord.Coord.change_units_other` default function
or use a custom function instead by using
:func:`constructor.Constructor.set_coords_units_conversion`.

This conversion will only happen if the 'units' attribute on the CoordScan
and its parent Coord are defined and different.
By default the CoordScan object will inherit the units of its parent Coord,
but this might not reflect the units inside the files !
You can set the CoordScan units by scanning attributes, or by accessing it::

  cstr.current_fg.cs['time'].units = '...'

The conversion will happen at the very end of the scanning process.


Variables Coordinates
---------------------

Variables are treated as coordinates when scanning, with some specificities.

When adding a filegroup to the constructor, one should not specify
the variables along with other coordinates.
A variables CS will automatically be added.
The user can specify what variables are in this filegroup using the `contains`
argument, but this only has a cosmetic purpose, making it easier to
differentiate filegroups.
The variables values still need to be set, either by scanning them like
any other coordinate, or setting it manully using
:func:`constructor.Constructor.set_variables_infile`.
Variables are considered 'in' by default, a flag can set it shared when
adding a filegroup.

Contrary to other CoordScan, the values are not sorted after being scanned.
Also, note the in-file index or values do not need be integers, it can be
string refering to the variable name.

One can scan variables specific attributes and put them into the
VariablesInfo object.


Reversing dimensions and empty dimensions
-----------------------------------------

Sometimes, no information on how the data is aranged can be found in the files.
One can still manually set values and in-file indices, but can also resort to
not give any information.
Then, the CS will remain empty.
The values are supposed identical to the available scope ones.
When loading data, the filegroup will simply transmit the asked key as is.

The user can still 'mirror' the key if he knows the dimension is upside-down
in the file. So each asked index will go through `i = CS.size - i`.

Still, the best is for the user to manually set information based on his
knowledge of the data.


Scanning in file
----------------

The scanning function is set by
:func:`Constructor.set_scan_in_file<constructor.Constructor.set_scan_in_file>`.
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

One should look into :func:`filegroup.coord_scan.scan_in_file_default` for
a better description of the function signature.
:mod:`data_loader.scan_library` contains some examples.


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
To this end, we use :class:`matchers<filegroup.matcher.Matcher>`.
This is a part of the pre-regex, enclosed in parenthesis and preceded
by a `%`. It specifies the coordinate name and the element of the coordinate.
The element dictate the regex that will be used for that matcher, and
how it will eventually be treated by the filename scanning function.

Various elements are already coded. Elements for dates and times follow
*strftime* format specifications.
For instance the element 'Y' designate a year. It will be replaced by a
regex searching for 4 digits and :func:`scan_library.get_date_from_matches`
will use this to create a date.


+----------------+-------------------------+--------------------------+
|  Element name  |          Regex          |                          |
+----------------+-------------------------+--------------------------+
|      idx       |          \\d*           |          Index           |
+----------------+-------------------------+--------------------------+
|      text      |        [a-zA-Z]*        |         Letters          |
+----------------+-------------------------+--------------------------+
|      char      |          \\S*           |        Character         |
+----------------+-------------------------+--------------------------+
|       x        |         %Y%m%d          |     Date (YYYYMMDD)      |
+----------------+-------------------------+--------------------------+
|       X        |         %H%M%S          |     Time (HHMMSS)        |
+----------------+-------------------------+--------------------------+
|       Y        |      \\d\\d\\d\\d       |       Year (YYYY)        |
+----------------+-------------------------+--------------------------+
|       m        |         \\d\\d          |        Month (MM)        |
+----------------+-------------------------+--------------------------+
|       d        |         \\d\\d          |    Day of month (DD)     |
+----------------+-------------------------+--------------------------+
|       j        |        \\d\\d\\d        |    Day of year (DDD)     |
+----------------+-------------------------+--------------------------+
|       B        |        [a-zA-Z]*        |        Month name        |
+----------------+-------------------------+--------------------------+
|       H        |         \\d\\d          |        Hour 24 (HH)      |
+----------------+-------------------------+--------------------------+
|       M        |         \\d\\d          |        Minute (MM)       |
+----------------+-------------------------+--------------------------+
|       S        |         \\d\\d          |       Seconds (SS)       |
+----------------+-------------------------+--------------------------+


Single letters preceded by a percentage in the regex will recursively be
replaced by the corresponding regex.
So `%X` will be replaced by `%H%M%S`. This still counts as a single matcher
and its element name will not be changed.
A percentage character can be escaped by another percentage (`%%`)

All the use cases are not covered, and one might want to use a specific
regex in place of the matcher::

  sst_%(time:Y:custom=\d\d:)-%(time:m)-%(time:d)

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
:func:`Constructor.set_scan_filename<constructor.Constructor.set_scan_filename>`.
The function receives a Coordscan instance, and values eventually scanned from
inside the same file if the in-file scanning was done before-hand.
It must returns one or more values and in-file indices.

One should look into :func:`filegroup.coord_scan.scan_filename_default` for
a better description of the function signature.
:mod:`data_loader.scan_library` contains some examples.
