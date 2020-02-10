
Filegroups
==========

A data object contains one or more filegroup.
This object manages a couple of tasks. It first does the scanning of all
datafiles to find the various coordinates values.
It also manages the loading of the data (actually opening the files), to
do this, it must first look into the files to see how the data is arranged.

The scanning functionalities are written in the
:class:`FilegroupScan<data_loader.filegroup.filegroup_scan.FilegroupScan>`.
The loading functions are specified in the class
:class:`FilegroupLoad<data_loader.filegroup.filegroup_load.FilegroupLoad>`.
The former is to be subclassed for file-format specific functions.


Pre-regex
---------

Most of the scanning is coordinate specific, thus it is mainly handled
by :class:`CoordScan<data_loader.coord_scan.CoordScan>`
objects (see :doc:`scanning`).
The filegroup orchestrate the scanning, and is also responsible for
variables attribute scanning, and filename scanning.

To find informations in the filename, and keep track of how it
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

+----------------+-------------------------+------------------+
|  Element name  |          Regex          |                  |
+----------------+-------------------------+------------------+
|      idx       |          \\d*           |       Index      |
+----------------+-------------------------+------------------+
|      text      |        [a-zA-Z]*        |      Letters     |
+----------------+-------------------------+------------------+
|      char      |          \\S*           |     Character    |
+----------------+-------------------------+------------------+
|        x       |     \d\d\d\d\d\d\d\d    |       Date       |
+----------------+-------------------------+------------------+
|        Y       |      \\d\\d\\d\\d       |       Year       |
+----------------+-------------------------+------------------+
|       mm       |         \\d?\\d         |       Month      |
+----------------+-------------------------+------------------+
|       dd       |         \\d?\\d         |    Day of month  |
+----------------+-------------------------+------------------+
|       doy      |       \\d?\\d?\\d       |    Day of year   |
+----------------+-------------------------+------------------+
|        M       |        [a-zA-Z]*        |    Month name    |
+----------------+-------------------------+------------------+


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

The filegroup also manages the loading of data. It receives from the database
object the variables to load, and the parts of the coordinates to load.
The filegroup ellaborates a list of 'loading commands', which contain the file
to open, the parts of the data to take from that file, and where to put them in
the data array in memory.
The filegroup then execute each command.

Hereafter, we will refer to 'keys' as the object used to define a part of the
data. It can be a list of integers, or a slice.


Creation of loading commands
++++++++++++++++++++++++++++

Note that, hopefully, you should not have to temper with the construction of the
commands.

The first step is to retrieve the files to load, thus by working with the shared
coordinates.
No full filenames are stored. Rather, for each coordinate, the matches
from the pre-regex corresponding to that coordinate are kept for each coordinate
value.
This avoid storing an excessive number of long filenames, especially if there
are multiple shared coordinates.
With the matches from all the shared coordinates, we can reconstruct the
filename, by replacing the matchers in the pre-regex.
In the process we also retrieve the in-file index.

At this point, we have a list of commands, each containing one key.
The in-file key should be an integer or None.
Commands for the same file are merged together.
We now possibly have multiple integers keys in the same file.
This would be the case for files containing multiple steps for a shared
coordinate.
Rather than loading one step by one step, the keys are merged together when
possible. Two keys differing by only one coordinate are merged, and lists are
transformed into slices.

    key 1: time=0, depth=0
    key 2: time=2, depth=0
    key 3: time=4, depth=0

would be transformed into::

    key 1: time=[0, 2, 4], depth=0

and then::

    key 1: time=slice(0, 5, 2), depth=0

Of course, the in-file keys are modified along with the memory keys.

Once the shared coordinates are taken care of, the in-file and memory keys
for in coordinate are constructed, and added to all the commands.
The keys are finally ordered as specified in the data base.

Importantly, when the user ask for a key, the key is reversed if the
coordinate is considered 'index descending' for that filegroup.
More information in :ref:`Reversing dimensions`.


Executing the command
+++++++++++++++++++++

The construction of the loading commands is completely remote from the file
format. The only function to depend on the file format is
:func:`load_cmd<data_loader.filegroup.FilegroupLoad.load_cmd>`.
Thus, to add a file format, one has to mainly rewrite this function, as
well as two functions that open and close a file.

The function takes a single command and a file object in argument.
The file object is created by
:func:`open_file<data_loader.filegroup.filegroup_scan.FilegroupScan.open_file>`.
For each key in the command, the function should take a 'chunk' of data
corresponding to the in-file key.

One should pay attention to the way the data is organized. The dimension
order might not be the same as in the data object.
The file format might permit to retrieve this order, otherwise the order
of the coordinates indicated to the filegroup at its creation is used.
The data chunk may has to be reordered to fit into the data array.
This is done by the
:func:`reorder_chunk<data_loader.filegroup.FilegroupLoad.reorder_chunk>`
function.

Note that the loading should be robust against coordinates mismatch.
It is for example possible to ask for a key that is not present in the file.
This is done by sending a `None` in-file key.
It is also possible to have dimensions in the file that are not known by
the filegroup or database. In this case, the first index of that dimension
is taken.

Once reorder, the data chunk is placed into the data array at the specified
memory key.

For more information on subclassing for a new file format: :ref:`File formats`
