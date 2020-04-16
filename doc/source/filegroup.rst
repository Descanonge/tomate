
.. currentmodule:: data_loader


Filegroups
==========

A data object contains one or more filegroup.
This object manages a couple of tasks. It first does the scanning of all
datafiles to find the various coordinates values.
It also manages the loading of the data (actually opening the files).

The scanning functionalities are written in the
:class:`FilegroupScan<filegroup.filegroup_scan.FilegroupScan>`.
The loading functions are specified in the class
:class:`FilegroupLoad<filegroup.filegroup_load.FilegroupLoad>`,
subclass of FilegroupScan.
The latter is to be subclassed for file-format specific functions.


Loading
-------

The filegroup manages the loading of data. It receives from the database
object the parts of each dimensions to load.
The filegroup ellaborates a list of 'loading commands', which contain the file
to open, the parts of the data to take from that file (in-file keys),
and where to put them in the data array in memory (memory keys).
The filegroup then execute each command.

All this process relies heavily on keys and keyrings as defined in
:ref:`Keys and keyrings`.


Creation of loading commands
++++++++++++++++++++++++++++

Note that, hopefully, you should not have to temper with the construction of the
commands. This is mostly intended for developpers and if the need to debug
or change this process should arise.

Loading starts in the DataBase object, where the user specify parts of each
dimension to load.
This is transmitted to each filegroup, in the form of a keyring containing
indices of the available scope.
The filegroup converts this into its own scope. It keeps part of demanded data
that it contains and find the appropriate memory keyring (that is still in
available scope).

We then need to retrieve the files to load, thus by working with the shared
coordinates. In the process we also retrieve the in-file index for shared
coordinates.

At this point, we have a list of commands, each containing one key.
The memory keys for the shared coordinate each have been split.
The in-file key should be an integer or None.
Commands for the same file are merged together.
We now possibly have multiple integers keys in the same file,
as this would be the case for files containing multiple steps for a shared
coordinate.
Rather than loading one step by one step, the keys are merged together when
possible. Two keys differing by only one coordinate are merged, and lists are
transformed into slices.
For instance::

    key 1: time=0, depth=0
    key 2: time=2, depth=0
    key 3: time=4, depth=0

would be transformed into::

    key 1: time=[0, 2, 4], depth=0

and then::

    key 1: time=slice(0, 5, 2), depth=0

Of course, the in-file keys are modified along with the memory keys.

Once the shared coordinates are taken care of, the in-file and memory keys
for in coordinates are constructed, and added to all the commands.
Lists of length one are transformed in integers.
The keys are finally ordered as specified in the data base.

For some file formats, variables cannot be retrieved all at once as if
they were in a contiguous array.
All commands are then duplicated in as many copies as there are variables
(see
:func:`FilegroupNetCDF.get_commands<filegroup.filegroup_netcdf.FilegroupNetCDF.get_commands>`).


Executing the command
+++++++++++++++++++++

The construction of the loading commands is completely remote from the file
format. The only function to depend on the file format is
:func:`load_cmd<filegroup.filegroup_load.FilegroupLoad.load_cmd>`.
Thus, to add a file format, one has to mainly rewrite this function, as
well as two functions that open and close a file.

The function takes a single command and a file object in argument.
The file object is created by
:func:`open_file<filegroup.filegroup_scan.FilegroupScan.open_file>`.
For each key in the command, the function should take a 'chunk' of data
corresponding to the in-file key.

One should pay attention to the way the data is organized. The dimension
order might not be the same as in the data object.
The file format might permit to retrieve this order, otherwise the order
of the coordinates indicated to the filegroup at its creation is used.
The data chunk may have to be reordered to fit into the data array.
This is done by the
:func:`reorder_chunk<filegroup.filegroup_load.FilegroupLoad.reorder_chunk>`
function.
One should also remember that dimensions could be squeezed when
taken from the file by the in-file keyring.
The memory keyring should have an identical shape as the data chunk.
:class:`filegroup.filegroup_netcdf.FilegroupNetCDF` might provide an
useful example for those wanting to dwell on those (important) details.

Note that the loading should be robust against coordinates mismatch.
It is for example possible to ask for a key that is not present in the file.
This is done by sending a `None` in-file key.
It is also possible to have dimensions in the file that are not known by
the filegroup or database, or that have different names than those from
the database.
In this case, the first index of that dimension is taken.
Thoses issues are taken care of by
:func:`_get_internal_keyring<filegroup.filegroup_load.FilegroupLoad._get_internal_keyring>`.

Once reordered, the data chunk is placed into the data array at the specified
memory key.

For more information on subclassing for a new file format: :ref:`File formats`
