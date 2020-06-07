
.. currentmodule :: data_loader


Constructing a database
=======================

A data object needs a few objects to be functionnal, namely: coordinates,
a vi, and filegroups.
The constructor object provides ways to easily create a data object,
and conduct the scanning if the data is on disk.

This page will break down a typical database creation script, and present
the main features of the package.


Adding Coordinates
------------------

First we will define the coordinates that we will encounter in our database.
Here we use a simple :class:`Coord<coordinates.coord.Coord>` for the latitude and
longitude, and :class:`Time<coordinates.time.Time>` for the time as this will provide
useful functionalities for working with dates.
We could use any kind of subclass of the Coord class, eventually a user made one.

::

    from data_loader import Coord, Time
    lat = Coord('lat', None, fullname='Latitude')
    lon = Coord('lon', None, fullname='Longitude')
    time = Time('time', None, fullname='Time',
                units='hours since 1970-01-01 00:00:00')

    coords = [lat, lon, time]

Since we do not yet have the coordinates values, we specify `None`.
We must include a CF-metadata compliant units for the time coordinate.

The order of `coords` is of great importance, as this will dictate in what
order the data will be stored. Here the ranks of the data numpy array will be
(variables, lat, lon, time).
The variables dimension does not need to be created by the user. The constructor
will take care of it.


Adding filegroups
-----------------

We now create the filegroups which each represent a group of similar files on
disk.
The filegroup stores information on how the data is arranged on disk, and
is responsible for finding this information during the scanning process.

Our files are organized as such::

    Data
    ├── SSH
    │   ├── SSH_20070101.nc
    │   ├── SSH_20070109.nc
    │   └── ...
    └── SST
        ├── A_2007001_2010008.L3m_8D_sst.nc
        ├── A_2007008_2010016.L3m_8D_sst.nc
        └── ...

Both group of files have a single file per time-step (an 8 day average).
The SSH files contain information about that time-step: there is a
time dimension and variable from which we can extract the time values for
that file.
For the SST on the other hand, the sole information on the time value for each
step is found in the filename.
For both file groups, the latitude and longitude are contained in each file, and
do not vary from file to file.
Note this example is in no way a requirement, the package can accomodate with
many more ways of organizing data in various subfolders and files.

We start by importing a FilegroupLoad subclass, here all both filegroups are NetCDF,
so we will use FilegroupNetCDF.

::

    from data_loader.filegroup import FilegroupNetCDF


We add the first filegroup for the SSH::

    coords_fg = [[lon, 'in', 'longitude'],
                 [lat, 'in', 'latitude'],
                 [time, 'shared']]
    cstr.add_filegroup(FilegroupNetCDF, coords_fg, name='SSH', root='SSH')

The `coords_fg` variable specify how are arranged the coordinates.
The 'in' flag means the whole coordinate/dimension is found in each file,
and that it is arranged in the same way for all files.
The 'shared' flag means the dimension is splitted accross multiple files.
The spatial dimensions in our files are named differently from ours, so we
specify it. Time is found under the same name so we say nothing.
We give a name for our filegroup, this will help in debugging.
We give a subfolder in which the files are found,
if not precised, the root directory from the constructor will be used.

We must now tell where are the files, and more precisely how are constructed
their filenames. By filename, we mean the whole string starting after the
root directory, folders included.
For that, a pre-regex is used. It is a regular expression with a few
added features. It will be transformed in a standard regex that will be
used to find the files.
I can only recommend to keep the regex simple...

Any regex in the pre-regex will be matched with the first file found, and then
*considered constant accross all files*. For instance, using ``SST/A_.*\.nc``,
a valid regex that would match all SST files, won't work the way intended.
The filegroup will consider that all files are in fact equal to the first
filename that matched ('SST/A\_2007001-2007008.nc' here).

For that reason, we must tell for what coordinates the filenames are varying.
We use :class:`Matchers<filegroup.matcher.Matcher>`::

    pregex = r"SSH_%(time:x)\.nc"

Let's break it down. Each variation is notified by \% followed in parenthesis
by the coordinate name, and the element of that coordinate.
Here 'x' means the match will be the date: the matcher will be replaced by
the correspond regex (8 digits in this case, YYYYMMDD), and the string found in each
filename will be used to find the date.
The elements available are defined in the
:class:`Matcher<filegroup.matcher.Matcher>` class.
(see :ref:`Scanning filename` for a list of defaults elements)
For more complicated and longer filenames, we can specify some replacements.
We obtain::

    pregex = ('%(prefix)_'
              '%(time:x)'
              '%(suffix)')
    replacements = {'prefix': 'SSH',
                    'suffix': r'\.nc'}
    cstr.set_fg_regex(pregex, **replacements)

Don't forget the r to allow for backslashes, and to appropriately
escape special characters in the regex.

The next step is to tell the filegroup how to scan files for
additional information. This is done by appointing scanning functions
to the filegroup. The appointement is coordinate specific.
First, we must specify how to retrieve the coordinates values,
and in-file indices by looking at the filename, and/or inside the file.
This is done by standardized user functions. There are a number of
pre-existing functions that can be found in
:mod:`scan_library<data_loader.scan_library>`.
Here, all coordinates values are found in the netCDF files, we use an existing
function::

    import data_loader.scan_library as scanlib
    cstr.set_scan_in_file(scanlib.nc.scan_in_file, 'lat', 'lon', 'time')

We must also tell how the variable are organized in the files::

    cstr.set_variables_infile(SSH='sea surface height')

This will tell the filegroup to look for the variable 'sea surface height' in
the netCDF file when loading data.
We now do the same process for the SST files. As their structure is a bit more
complicated, we can explore some more advanced features of the pre-regex.
First, we notice there are two varying dates in the filename, the start and end
of the 8-days averaging. We only want to retrieve the starting date, but must
still specify that there is a second changing date. To discard that second part,
we add the `dummy` flag to the end of the matchers.
This is useful to specify variations that are not associated with
any coordinate value::

    pregex = ('%(prefix)_'
              '%(time:Y)%(time:doy)_'
              '%(time:Y:dummy)%(time:doy:dummy)'
              '%(suffix)')
    replacements = {'prefix': 'SSH',
                    'suffix': r'\.nc'}
    cstr.set_fg_regex(pregex, **replacements)

Here we used the `Y` ant `doy` elements, for 'year' and 'day of year'.
Let's pretend the 'day of year' element was not anticipated within the package.
We need to specify the regex that should be used to replace the matcher in
the pre-regex. We can modify the Matcher class, but that would be cumbersome.
Instead, we specify that we are using a custom regex::

    r'%(time:Y)%(time:doy:custom=\d\d\d:)'

The regex will now expect a `doy` element with three digits. Note that the
custom regex **must end with a colon**. It can still be followed by the
`dummy` keyword.

We must again tell how the coordinate will be scanned. This time the
date information will be retrieved from the filename::

    cstr.set_variables_infile(SST='sst')
    cstr.set_scan_in_file(scanlib.nc.scan_in_file, 'lat', 'lon')
    cstr.set_scan_filename(scanlib.get_date_from_matches, 'time', only_value=True)

Only the time value will be fetch from the filename, so as we specify nothing for
the time in-file index it will stay None for all time values.
A None in-file index tells the filegroup that there is no time dimension for the
data in file.
Note that specifying the `only_values` keyword is actually superfluous as
`get_date_from_matches` return a `(value, None)` tuple.

The values and index of the coordinates is not the only thing we can scan for.
The filegroup can look for coordinate specific attributes. This will only affect
the scanning coordinate object.
For instance::

    cstr.set_scan_coords_attributes(scanlib.nc.scan_units, 'time')

will get the time units in file.
For more details on scanning coordinate units, look at :ref:`Units conversion`.

We can also scan for general attributes that will be placed in the VI
as 'infos'::

    cstr.set_scan_general_attributes(scanlib.nc.scan_infos)

and variables specific attributes that will be placed in the VI as attributes::

    cstr.set_scan_variables_attributes(scanlib.nc.scan_variables_attributes)

Conversely, we can also manually add information to the VI::

    cstr.vi.set_attrs
    cstr.vi.set_infos


The scanning will not overwrite information already present in the VI.

The last step is to tell what kind of database object we want. If we say
nothing, the basic :class:`data_base.DataBase` will be used.
If we want to add on-disk data management (scanning and loading data), we can
use
:func:`Constructor.add_disk_features<constructor.Constructor.add_disk_features>`.
Note this is automatically done if at least one filegroup was added to the
constructor, or if we keep the 'scan' flag to its default (True) when creating
the database.

We can add more functionalities by specifying additional child classes of
DataBase. All of those provided by the package are present in the
:mod:`data_loader.db_types`.
Here let's use :class:`DataMasked<db_types.data_masked.DataMasked>` that add support
for masked data, and :class:`DataPlot<db_types.data_plot.DataPlot>` which provides
convenience plotting functions::

  import data_loader.db_types as dt
  cstr.set_data_types([dt.DataMasked, dt.DataPlot])

More details on adding functionalities: :ref:`Additional methods`.


The data object
---------------

Now that everything is in place, we can create the data object::

  db = cstr.make_data()

The line above will start the scanning process. Each filegroup will
scan their files for coordinates values and indices. The values obtained
will be compared.
If the coordinates from different filegroups have different values, only
the common part of the data will be available for loading.
(Note this is a default behavior, for more advanced features, see
:ref:`Multiple filegroups`)

During the scanning of the file, information is logged at the 'debug' level.
More information on logging: :doc:`log`.


Loading data
------------

We can now load data !
For that, we must specify what part of the data we want.
This is done by specifiying indices for each dimensions.
If a dimension is omitted, it will be taken entirely.
Parts of a coordinate must be selected with an integer,
a list of integer, or a slice.
The variables dimension is special in that one can
specify variables names instead of their index.

For instance::

    # Load all SST
    db.load(var='SST')

    # Load first time step of SST and SSH
    db.load(['SST', 'SSH'], time=0)

    # Load a subpart of all variables.
    db.load(['SSH', 'SST'], lat=slice(0, 500), lon=slice(200, 800))

    # Load by value instead of index
    slice_lat = db.avail.lat.subset(10., 30.)
    db.load(lat=slice_lat)
    # or directly
    db.load_value(lat=slice(10., 30.))

    print(db.data)

After loading data, the coordinates of the corresponding scope ('loaded')
will be adjusted, so that the coordinates are in sync with the data.

Once loaded, the data can be sliced further using::

    db.slice_data('SST', time=[0, 1, 2, 5, 10])


To go further
-------------

| More information on the data object: :doc:`data`
| More information on scanning: :doc:`scanning`
| More information on logging: :doc:`log`

Some examples of database creation and use cases are provided
in /examples.
