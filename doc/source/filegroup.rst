
Filegroups
==========

A data object contains one or more filegroup.
This object manages a couple of tasks. It first does the scanning of all
datafiles to find the various coordinates values.
It also manages the loading of the data (actually opening the files).

The scanning functionalities are written in the
:class:`FilegroupScan<data_loader.filegroup.filegroup_scan.FilegroupScan>`.
The loading functions are specified in the abstract class
:class:`FilegroupLoad<data_loader.filegroup.filegroup_load.FilegroupLoad>`.
This class is to be subclassed for file-format specific functions.


Pre-regex
---------

The filegroups actually only look at the filenames to see if they match
the pattern specified by the user.
The actual scanning is done by :class:`CoordScan<data_loader.coord_scan.CoordScan>`
objects (see :doc:`scanning`).

To find informations in the filename, and keep track of how they
changes along a dimension, we must tell the database the structure of
the filenames. This is done using a pre-regex: a regular expression with
added features.

Any regex can be used in the pre-regex, however, it will be replaced
by its match as found in the first file and then considered constant.
For example, if we have daily files 'sst_2003-01-01.nc' with the
date changing for each file. We could use the regex `sst_.*\.nc`, which
would match correctly all files, but the program would consider that
*all* filenames are 'sst_2003-01-01.nc'

Instead, we must specify what part of the filename varies, and along
with which dimension / coordinate.
To this end, we use :class:`Matchers<data_loader.coord_scan.Matcher>`.
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

+----------------+---------------+------------------+
|  Element name  |     Regex     |                  |
+----------------+---------------+------------------+
|      idx       |      \\d*     |       Index      |
+----------------+---------------+------------------+
|      text      |   [a-zA-Z]*   |      Letters     |
+----------------+---------------+------------------+
|      char      |      \\S*     |     Character    |
+----------------+---------------+------------------+
|        Y       | \\d\\d\\d\\d  |       Year       |
+----------------+---------------+------------------+
|       mm       |    \\d?\\d    |       Month      |
+----------------+---------------+------------------+
|       dd       |    \\d?\\d    |    Day of month  |
+----------------+---------------+------------------+
|       doy      |  \\d?\\d?\\d  |    Day of year   |
+----------------+---------------+------------------+
|        M       |   [a-zA-Z]*   |    Month name    |
+----------------+---------------+------------------+


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


Loading
-------

TODO...
