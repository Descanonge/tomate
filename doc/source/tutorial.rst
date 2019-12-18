
Constructing a database
=======================

A database needs a few objects to be functionnal, namely coordinates,
a vi, and filegroups. Creating these can be a bit daunting. The
constructor module provides ways to create a data object, and do a couple
of additional checks.

This page will break down a typical database creation script.


Coordinates
-----------

First we will define the coordinates that we will encounter in out database.
Here we use a simple :class:`Coord<data_loader.Coord>` for the latitude and
longitude, and :class:`Time<data_loader.Time>` for the time as this will provide
useful functionalities for working with dates.
We could use any kind of subclass of the Coord class.

::

   from data_loader import Coord, Time
   lat = Coord('lat', None, fullname='Latitude', name_alt='latitude')
   lon = Coord('lon', None, fullname='Longitude', name_alt='longitude')
   time = Time('time', None, fullname='Time',
                unit='hours since 1970-01-01 00:00:00')

   coords = [lat, lon, time]

Since we do not yet have the coordinates values, we specify `None`.
We must include a CF-metadata compliant unit for the time coordinate.

'lat', 'lon', and 'time' will be the names of our coordinates, however
they could be found under other names in our different data files, we thus
specify a `name_alt` parameter. We could add any number of alternative names
by using a list of strings.

The order of `coords` is of great importance, as this will dictate in what
order the data will be stored. Here the ranks of the data numpy array will be
(lat, lon, time).


Variables
---------

We must now specify the variables we are intersted in. We will construct a
:doc:`VariablesInfo<variables_info>` object. For each variable we will specify
its name and a serie of attributes.

::

   from data_loader.constructor import VIConstructor

   vic = dlc.VIConstructor()

   name = "SST"
   infos = {'fullname': 'Sea Surface Temperature',
            'ncname': 'sst',
            'unit': 'deg C',
            'vmin': -2, 'vmax': 30}
   vic.add_var(name, infos)

   name = "SSH"
   infos = {'fullname': 'Sea Surface Height',
            'ncname': 'ssh'}
   vic.add_var(name, infos)

We specified two variables, with different attributes. We can now construct the
vi object::

  vi = vic.make_vi()


Filegroups
----------

The lasts objects to create are the filegroups. They hold information on
where the files are, what variables they contain, and what parts of the
dimensions.
The filegroups are also responsible for opening those files
later on for loading the data. We must thus give them some of that information.

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

We start by importing the filegroup constructor, and a FilegroupLoad subclass,
here all our files are NetCDF, so we will use FilegroupNetCDF.
We must supply a root directory, where all files are contained, as well as
the vi.

::

   from data_loader.constructor import FGConstructor
   from data_loader.filegroup import FilegroupNetCDF

   fgc = FGConstructor('/Data/', coords)

We add the first filegroup for the SSH::

  contains = ['SSH']
  coords_fg = [[lon, 'in'], [lat, 'in'], [time, 'shared']]
  fgc.add_fg(FilegroupNetCDF, contains, coords_fg)

We first tell what variables are placed in this filegroup. There
can be as many variable as wanted, but a variable cannot be distributed
accross multiple filegroups.
The `coords_fg` variable specify how are arranged the coordinates.
The 'in' flag means the whole coordinate/dimension is found in each file.
The 'shared' flag means the dimension is splitted accross multiple files.
The order of the coordinates does not matter here.

We must now tell where are the files, more precisely how is constructed
their filenames. By filename, we mean the whole string starting after the
root directory.
For that, a pre-regex is used. It is a regular expression, with a few
added features. It will be transformed in a more standard regex that will be
used to find the files.
I can only recommend to keep the regex simple...

Any regex in the pre-regex will be matched with the first file found, and then
*considered constant accross all files*. For instance, using `SST/A_.*\.nc`, a
valid regex that would match all SST files, won't work the way intended. The
filegroup will consider that all files are in fact equal to the first
filename that matched ('SST/A_2007001-2007008.nc' here).

For that reason, we must tell for what coordinates the filenames are varying.
Here only the time is changing across files. We use for that
:class:`Matchers<data_loader.coord_scan.Matcher>`::

       pregex = r"SSH/SSH_%(time:Y)%(time:mm)%(time:dd)\.nc"

Let's break it down. Each variation is notified by \% followed in parenthesis
by the coordinate name, and the element of that coordinate.
Here 'Y' means the match will be the date year, the matcher will be replaced by
the correspond regex (4 digits in this case). This element name will also be
used to extract information from the filename.
The default elements available are found in the
:class:`Matcher<data_loader.coord_scan.Matcher>` class.
(see :doc:`scanning`)

To simplify a bit the pre-regex, we can specify some replacements. We obtain::

  pregex = ('%(dir)/%(prefix)_'
            '%(time:Y)%(time:mm)%(time:dd)'
            '%(suffix)')
  replacements = {'dir': 'SSH/',
                  'prefix': 'SSH',
                  'suffix': r'\.nc'}
  fgc.set_fg_regex(pregex, replacements)

Don't forget the r to allow for backslashes.

The last step is to specify how to retrieve the coordinates values,
either by looking at the filename, or inside the file.
This is done by standardized functions. You can use existing functions, or
write your own. Here, all coordinates values are found in the netCDF files.
We use an existing function::

  import data_loader.scan_library as scanlib
  fgc.set_scan_in_file_func(scanlib.scan_in_file_nc, 'lat', 'lon', 'time')

We now do the same process for the SST files. As their structure is a bit more
complicated, we can explore some more advanced features of the pre-regex.
First, we notice they are two varying dates in the filename, the start and end
of the 8-days averaging. We only want to retrieve the starting date, but must
still specify that there is a second changing date. To discard that second part,
we add the `dummy` flag to the end of the matchers.
This is a very useful trick to specify variation that are not associated with
any coordinate value::

  pregex = ('%(dir)/%(prefix)_'
            '%(time:Y)%(time:doy)_'
            '%(time:Y:dummy)%(time:doy:dummy)'
            '%(suffix)')
  replacements = {'dir': 'SSH/',
                  'prefix': 'SSH',
                  'suffix': r'\.nc'}
  fgc.set_fg_regex(pregex, replacements)

Here we used the `doy` element, for 'day of year'.
Let's pretend this possibility was not anticipated within the package.
We need to specify the regex that should be used to replace the matcher in
the pre-regex. We can modify the Matcher class, but that would be cumbersome.
Instead, we specify that we are using a custom regex::

  r'%(time:Y)%(time:doy:custom=\d\d\d:)'

The regex will now expect a `doy` element with three digits. Note that a
custom **must be ended by a colon**. It can still be followed by the
`dummy` keyword.

We must again tell how the coordinate will be scanned. This time the
date information will be retrieved from the filename::

  fgc.set_scan_in_file_func(scanlib.scan_in_file_nc, 'lat', 'lon')
  fgc.set_scan_filename_func(scanlib.get_date_from_matches, 'time')


The Data Object
---------------

Now that everything is in place, we can create the database.
The last information needed is the type of database we want to use.
This can be any subclass of
:class:`DataBase<data_loader.DataBase>` with additional functionnalities.
Here we will use :class:`DataMasked<data_loader.masked.DataMasked>`, adapted
for data with masked values::

  from data_loader.masked import DataMasked
  dt = fgc.make_database(DataMasked, vi)

The lines above will start the scanning process. Each filegroup will
scan their files for coordinates values and index. The values obtained
will be compared.
If the coordinates from different filegroups have different ranges, only
the common part of the data will be available.


Loading Data
------------

We can now load data !
For that, we must specify the variables, and
what part of the dimensions we want. We can only specify
an integer, a list of integers, or a slice.
A function to append data to what is already loaded is on
its way, and will allow more complexity in what can be loaded.

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
