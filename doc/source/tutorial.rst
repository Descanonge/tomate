
Constructing a database
=======================

A data object needs a few objects to be functionnal, namely coordinates,
a vi, and filegroups. Creating these can be a bit daunting. The
constructor module provides ways to create a data object, and do a couple
of additional checks that ease the creation of a database.

This page will break down a typical database creation script, and present
the main features of the package.


Adding Coordinates
------------------

First we will define the coordinates that we will encounter in our database.
Here we use a simple :class:`Coord<data_loader.Coord>` for the latitude and
longitude, and :class:`Time<data_loader.Time>` for the time as this will provide
useful functionalities for working with dates.
We could use any kind of subclass of the Coord class, eventually a user made one.

::

    from data_loader import Coord, Time
    lat = Coord('lat', None, fullname='Latitude', name_alt='latitude')
    lon = Coord('lon', None, fullname='Longitude', name_alt='longitude')
    time = Time('time', None, fullname='Time',
                units='hours since 1970-01-01 00:00:00')

    coords = [lat, lon, time]

Since we do not yet have the coordinates values, we specify `None`.
We must include a CF-metadata compliant units for the time coordinate.

'lat', 'lon', and 'time' will be the names of our coordinates, however
they could be found under other names in our different data files, we thus
specify a `name_alt` parameter. We could add any number of alternative names
by using a list of strings.

The order of `coords` is of great importance, as this will dictate in what
order the data will be stored. Here the ranks of the data numpy array will be
(lat, lon, time).


Adding Variables
----------------

We must now specify the variables we are interested in. This will construct a
:doc:`VariablesInfo<variables_info>` object (abbreviated VI).
For that, we will use a :class:`Constructor<data_loader.constructor.Constructor>` object.
We must supply a root directory, where all files are contained, as well as
the coordinates created before.
For each variable we will specify its name and eventually a serie of attributes.

::

    from data_loader.constructor import Constructor

    cstr = Constructor('/Data/', coords)

    name = "SSH"
    infos = {'fullname': 'Sea Surface Height',
             'ncname': 'ssh'}
    cstr.add_variable(name, **infos)

    name = "SST"
    infos = {'fullname': 'Sea Surface Temperature',
             'ncname': 'sst',
             'units': 'deg C',
             'vmin': -2, 'vmax': 30}
    cstr.add_variable(name, **infos)


If more information can be found in the files, we can set the filegroups to
scan for them a little latter. This will overide the attributes we set.
Note that we indicated the 'ncname' attribute that will be detrimental for scanning
netCDF files.


Adding filegroups
-----------------

We now create the filegroups.
They are responsible for scanning the files at the database
creation to see how the data is arranged and to find the coordinates
values, and opening those files later on for loading the data.
We must thus give them all the information necessary to accomplish those
tasks.

A filegroup regroups similar files that have the same format,
that contain the same variables, and in whiwh the data is arranged
in the same fashion.

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
For both file groups, the latitude and longitude are in each file, and do not
vary from file to file.
Note this example is in no way a requirement, the package can accomodate with
many more ways of organizing data in various subfolders and files.

We start by importing a FilegroupLoad subclass, here all our files are NetCDF,
so we will use FilegroupNetCDF.

::

    from data_loader.filegroup import FilegroupNetCDF


We add the first filegroup for the SSH::

    contains = ['SSH']
    coords_fg = [[lon, 'in'], [lat, 'in'], [time, 'shared']]
    cstr.add_filegroup(FilegroupNetCDF, contains, coords_fg, root='SSH')

We first tell what variables are placed in this filegroup. There
can be as many variables as wanted, but a variable cannot be distributed
accross multiple filegroups.
The `coords_fg` variable specify how are arranged the coordinates.
The 'in' flag means the whole coordinate/dimension is found in each file,
and that it is arranged in the same way for all files.
The 'shared' flag means the dimension is splitted accross multiple files.
The order of the coordinates does not matter here.
Eventually, we can add a subfolder in which the files are found,
if not precised, the root directory from the constructor will be used.

We must now tell where are the files, more precisely how is constructed
their filename. By filename, we mean the whole string starting after the
root directory.
For that, a pre-regex is used. It is a regular expression with a few
added features. It will be transformed in a standard regex that will be
used to find the files.
I can only recommend to keep the regex simple...

Any regex in the pre-regex will be matched with the first file found, and then
*considered constant accross all files*. For instance, using `SST/A_.*\.nc`, a
valid regex that would match all SST files, won't work the way intended. The
filegroup will consider that all files are in fact equal to the first
filename that matched ('SST/A_2007001-2007008.nc' here).

For that reason, we must tell for what coordinates the filenames are varying.
We use for that :class:`Matchers<data_loader.coord_scan.Matcher>`::

    pregex = r"SSH_%(time:Y)%(time:mm)%(time:dd)\.nc"

Let's break it down. Each variation is notified by \% followed in parenthesis
by the coordinate name, and the element of that coordinate.
Here 'Y' means the match will be the date year: the matcher will be replaced by
the correspond regex (4 digits in this case), and the string found in each
filename will be used to find the date year.
The elements available are defined in the
:class:`Matcher<data_loader.coord_scan.Matcher>` class.
(see :ref:`Pre-regex` for a list of defaults elements)

To simplify a bit the pre-regex, we can specify some replacements. We obtain::

    pregex = ('%(prefix)_'
              '%(time:Y)%(time:mm)%(time:dd)'
              '%(suffix)')
    replacements = {'prefix': 'SSH',
                    'suffix': r'\.nc'}
    cstr.set_fg_regex(pregex, replacements)

Don't forget the r to allow for backslashes, and to appropriately
escape special characters in the regex.

The last step is to tell the filegroup how to scan files for
additional information. This is done by appointing scanning functions
to the filegroup. The appointement can be coordinate specific.
First, we must specify how to retrieve the coordinates values,
and eventually in-file indices,
either by looking at the filename, or inside the file.
This is done by standardized functions. There are a number of
pre-existing functions that can be found in
:mod:`scan_library<data_loader.scan_library>`,
but user-defined function can also be used.
Here, all coordinates values are found in the netCDF files, we use an existing
function::

    import data_loader.scan_library as scanlib
    cstr.set_scan_in_file_func(scanlib.scan_in_file_nc, 'lat', 'lon', 'time')

We now do the same process for the SST files. As their structure is a bit more
complicated, we can explore some more advanced features of the pre-regex.
First, we notice they are two varying dates in the filename, the start and end
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
    cstr.set_fg_regex(pregex, replacements)

Here we used the `doy` element, for 'day of year'.
Let's pretend this possibility was not anticipated within the package.
We need to specify the regex that should be used to replace the matcher in
the pre-regex. We can modify the Matcher class, but that would be cumbersome.
Instead, we specify that we are using a custom regex::

    r'%(time:Y)%(time:doy:custom=\d\d\d:)'

The regex will now expect a `doy` element with three digits. Note that the
custom regex **must be ended by a colon**. It can still be followed by the
`dummy` keyword.

We must again tell how the coordinate will be scanned. This time the
date information will be retrieved from the filename::

    cstr.set_scan_in_file_func(scanlib.scan_in_file_nc, 'lat', 'lon')
    cstr.set_scan_filename_func(scanlib.get_date_from_matches, 'time')

The values and index of the coordinates is not the only thing we can scan for.
The filegroup can look for variable specific attributes, and place them into
the VI.
For instance, for netCDF files::

    cstr.set_scan_variables_attributes_func(scanlib.scan_attributes_nc)

We can also scan for coordinate specific information.
Currently, only the `units` attribute can be
modified::

    cstr.set_scan_coords_attributes_func(scanlib.scan_units_nc, 'lon', 'lat')



The data object
---------------

Now that everything is in place, we can create the data object.
It is useful to add different kind of methods to our data object,
for different needs. For instance to add support for masked data,
or to add function to plot easily our data, or to compute specific
statistics on our data.
We could also want to combine those functionalities.

We thus instruct the constructor a class of data to use.
This can be a subclass of
:class:`DataBase<data_loader.DataBase>`, or a list of
subclasses.
In case multiple child classes are indicated, a new data type will
be dynamically created using those classes as bases. The order of that list
gives the priority in the method resolution (first one in the list is the
first class checked).

Here we will use :class:`DataMasked<data_loader.masked.DataMasked>`, adapted
for data with masked values, and
:class:`DataPlot<data_loader.data_plot.DataPlot>` which helps in plotting data::

    from data_loader.masked import DataMasked
    from data_loader.data_plot import DataPlot
    dt = cstr.make_data([DataPlot, DataMasked])

The lines above will start the scanning process. Each filegroup will
scan their files for coordinates values and index. The values obtained
will be compared.
If the coordinates from different filegroups have different ranges, only
the common part of the data will be available for loading.

During the scanning of the file, information is logged at the 'debug' level.
More information on logging: :doc:`log`


Loading data
------------

We can now load data !
For that, we must specify the variables, and
what part of the dimensions we want. We can only specify
an integer, a list of integers, or a slice.

For instance::

    # Load all SST
    dt.load_data('SST')

    # Load first time step of SST and SSH
    dt.load_data(['SST', 'SSH'], time=0)
    dt.load_data(None, 0)

    # Load a subpart of all variables.
    # The variables order in data is reversed
    dt.load_data(['SSH', 'SST'], lat=slice(0, 500), lon=slice(200, 800))

    print(dt.data)

After loading data, the coordinates of the data will be also sliced, so that the
coordinates are in sync with the data.

Once loaded, the data can be sliced further using::

    dt.slice_data('SST', time=[0, 1, 2, 5, 10])

If no data is currently loaded, we can still slice the coordinates.
In the following example, we prepare to slice only a small
window in our data. This underlines that whatever we already
loaded or sliced, when loading data we specify slices and indexes
with regard to what is available *on disk*::

    slice_lat = dt['lat'].subset(21., 40.)
    slice_lon = dt['lon'].subset(-70., -60.)
    dt.set_slice('SST', lat=slice_lat, lon=slice_lon)
    print(dt.shape, dt.vi.var, dt.slices)

    dt.load_data(dt.vi.var, **dt.slices)


To go further
-------------

| More information on the data object: :doc:`data`
| More information on scanning: :doc:`filegroup` and :doc:`scanning`
| More information on logging: :doc:`log`

Some examples of database creation and use cases are provided
in /examples.
