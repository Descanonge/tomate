
.. currentmodule :: tomate


Constructing a database
=======================

A data object needs a few objects to be functionnal, namely: coordinates, a vi,
and filegroups.
The constructor object provides ways to easily create a data object, and launch
the scanning if the data is on disk.

This page will break down a typical database creation script, and present the
main features of the package.


Adding Coordinates
------------------

First we will define the coordinates that we will encounter in our database.
We use subclasses of :class:`Coord<coordinates.coord.Coord>` that add some
specific functionalities for each coordinate::

    from tomate import Time, Lat, Lon
    lat = Lat()
    lon = Lon()
    time = Time(units='hours since 1970-01-01 00:00:00')

    coords = [lat, lon, time]

This will give default names for each coordinate ('lat', 'lon', and 'time').
Those can be changed.
We must include a CF-metadata compliant units for the time coordinate.

We then create a Constructor object that will help in creating a database::

    from tomate import Constructor
    cstr = Constructor('/Data/', coords)

The dimension for variables (*ie* containing the list of variables) does not
need to be created by the user. The constructor will take care of it.


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
The SSH files contain information about that time-step: there are a time
dimension and a time variable from which we can extract the time values for that
file.
For the SST on the other hand, the sole information on the time value for each
step is found in the filename.
For both file groups, the latitude and longitude are contained in each file, and
do not vary from file to file.
Note this example is in no way a requirement, the package can accomodate with
many more ways of organizing data in various subfolders and files.

We start by importing a FilegroupLoad subclass, here both filegroups are NetCDF,
so we will use FilegroupNetCDF::

    from tomate.filegroup import FilegroupNetCDF

We add the first filegroup for the SSH::

    coords_fg = [cstr.CSS('lat', name='latitude'),
                 cstr.CSS('lon', name='longitude'),
                 cstr.CSS('time', 'shared')]
    cstr.add_filegroup(FilegroupNetCDF, coords_fg, name='SSH', root='SSH')

The `coords_fg` variable specify how are arranged the coordinates, we use
a :class:`CoordScanSpec<filegroup.spec.CoordScanSpec>`
object for each scanning coordinate.
The spatial dimensions in our files are named differently from ours, so we
specify it. Time is found under the same name so we say nothing.
The 'shared' flag means the dimension is splitted accross multiple files.
By default scanning coordinates are 'in', which means the whole
coordinate/dimension is found in each file.
We give a name for our filegroup, this will help in debugging.
We give a subfolder in which the files are found, if not precised, the root
directory from the constructor will be used.

We must now tell where are the files, and more precisely how are constructed
their filenames. By filename, I mean the whole string starting after the root
directory, folders included.
For that, a **'pre-regex'** is used. It is a regular expression with a few added
features. It will be transformed in a standard regex that will be used to find
the files.

Any regex in the pre-regex will be matched with the first file found, and then
*considered constant accross all files*. For instance, we could use
``SST/A_.*\.nc``, a valid regex that would match all SST files, but it wouldn't
work the way intended. The filegroup would consider that all files are in fact
equal to the first filename that matched (``SST/A_2007001-2007008.nc`` here).

For that reason, we must tell for what coordinates the filenames are varying.
We use :class:`Matchers<filegroup.matcher.Matcher>`::

    pregex = r"SSH_%(time:x)\.nc"

Let's break it down. Each variation is notified by \% followed in parenthesis
by the coordinate name, and the element of that coordinate.
Here 'x' means the match will be the date: the matcher will be replaced by the
correspond regex (8 digits in this case, YYYYMMDD), and the string found in each
filename can be used to find the date.
See :ref:`Scanning filename` for more details on the pre-regex.
For more complicated and longer filenames, we can specify some replacements.
We obtain::

    pregex = '%(prefix)_%(time:x)%(suffix)'
    replacements = {'prefix': 'SSH',
                    'suffix': r'\.nc'}
    cstr.set_fg_regex(pregex, **replacements)

Don't forget the r to allow for backslashes, and to appropriately escape special
characters in the regex.

To load data, the filegroup needs for each of its dimensions: the dimensions
values, their indices inside the file, and for variables, the dimensions along
which they vary inside the file.
We can do it by hand, but can also appoint functions that will do the work for
us during a 'scanning' process: let's do that !
There are a number of pre-existing functions that can be found in
:mod:`scan_library<tomate.scan_library>`.
Here, all coordinates values are found inside the netCDF files::

    import tomate.scan_library as scanlib
    cstr.add_scan_in_file(scanlib.nc.scan_dims, 'lat', 'lon', 'time')
    cstr.add_scan_in_file(scanlib.nc.scan_variables, 'var')

We now do the same process for the SST files. As their structure is a bit more
complicated, we can explore some more advanced features of the pre-regex.
First, we notice there are two varying dates in the filename, the start and end
of the 8-days averaging. We only want to retrieve the starting date, but must
still specify that there is a second changing date. To discard that second part,
we add the `dummy` flag to the end of the matchers.
This is useful to specify variations that will be ignored by functions
retrieving coordinates values from matches::

    pregex = ('%(prefix)_'
              '%(time:Y)%(time:j)_'
              '%(time:Y:dummy)%(time:j:dummy)'
              '%(suffix)')
    replacements = {'prefix': 'SST',
                    'suffix': r'\.nc'}
    cstr.set_fg_regex(pregex, **replacements)

Here we used the `Y` and `j` elements, for 'year' and 'day of year'.
Let's pretend the 'day of year' element was not anticipated within the package.
We specify a custom regular expression that should be used to replace the
matcher in the pre-regex ::

    r'%(time:Y)%(time:j:custom=\d\d\d:)'

The regex will now expect a `j` element with three digits. Note that the custom
regex **must end with a colon**. It can still be followed by the `dummy`
keyword.

We must again tell how the coordinates will be scanned. This time the
date information will be retrieved from the filename, and we specify
the variable by hand::

    cstr.add_scan_in_file(scanlib.nc.scan_dims, 'lat', 'lon')
    cstr.set_variables_elements('SST', in_idx='sea_surface_temperature',
                                dims=['lat', 'lon'])

    cstr.add_scan_filename(scanlib.get_date_from_matches, 'time')
    cstr.set_elements_constant('time', in_idx=None)

Only the time value will be fetch from the filename, we need to tell the
filegroup that all infile indices for time are None. A None in-file index tells
the filegroup that there is no time dimension in file.

The values and index of the coordinates are not the only thing we can scan for.
The filegroup can look for coordinate specific attributes. This will only affect
the scanning coordinate object. For instance::

    cstr.add_scan_coords_attributes(scanlib.nc.scan_units, 'time')

will get the time units in file. This is very important when scanning
time values inside files.
For more details on scanning coordinate units, look at :ref:`Units conversion`.

We can also scan for general attributes that will be placed in the VI
as 'infos'::

    cstr.add_scan_general_attributes(scanlib.nc.scan_infos)

and variables specific attributes that will be placed in the VI as attributes::

    cstr.add_scan_variables_attributes(scanlib.nc.scan_variables_attributes)
    cstr.add_scan_variables_attributes(scanlib.nc.scan_variables_datatype)

Conversely, we can also manually add information to the VI::

    cstr.vi.set_attributes
    cstr.vi.set_infos

The scanning will not overwrite information already present in the VI.

The last step is to indicate some information on the variables, not in the
files, but how we want them arranged in the database.
See :doc:`variable` for details.
In this simple example, Tomate should be able to deduce those information for
the SSH (as it is automatically scanned). But for the SST it is preferable to
input it by hand::

   cstr.vi.set_attributes('SSH', datatype='f', dimensions=['time', 'lat', 'lon'])


Optionally, we can customize our database object by adding functionalities by
specifying additional child classes of DataBase.
All of those provided by the package are present in the :mod:`tomate.db_types`
module.
Here let's use :class:`DataPlot<db_types.plotting.data_plot.DataPlot>` which
provides plotting functions::

  import tomate.db_types as dt
  cstr.set_data_types([dt.DataPlot])

More details on adding functionalities: :ref:`Additional methods`.


The data object
---------------

Now that everything is in place, we can create the data object::

  db = cstr.make_data()

The line above will start the scanning process. Each filegroup will scan their
files for coordinates values and indices. The values obtained will be compared.
If the coordinates from different filegroups have different values, only the
common part of the data will be available for loading.
(Note this is a default behavior, for more advanced features, see
:ref:`Multiple filegroups`)

During the scanning of the file, information is logged at the 'debug' level.
More information on logging: :doc:`log`.


Loading data
------------

We can now load data! For that, we must specify what part of the data we want,
with indices (integers, lists of integers, or slices), or values with
`*_by_value` functions. Variables can be specified by their index in the
available scope, or their name. If a dimension is omitted, it will be taken
entirely.

For instance::

    # Load all SST
    db.load(var='SST')

    # Load first time step of SST and SSH
    db.load(['SST', 'SSH'], time=0)

    # Load a subpart of all variables.
    db.load(lat=slice(0, 500), lon=slice(200, 800))

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

Some examples of database creation and use cases are provided in
at `<https://github.com/Descanonge/tomate/blob/develop/examples>`__.
