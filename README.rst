Data Loader
===========

Data Loader provides ways to manipulate data under the form of a
multi-dimensional array.
It manages multiples variables, as well as the coordinates along
which the data varies.
It also provides multiple convenience functions to retrieve
subpart of the data, do computations, or plot the data.

The data can be retrieved from disk, where it can be arranged
in multiple ways and formats.
Information on the data, such as variable attributes,
or coordinates values can be retrieved automatically.

**This is still in alpha, use at your own risk !**


Features
--------

For data in memory:

- Keep information about the data, the variables, the coordinates.
  All this information is in sync with the data.
- Select subparts of data easily.
- Use and create convenience function for analysis, plotting,...

For data on disk:

- Load data that spans multiple files and comes from different sources easily.
  Different file format ? different structure: rows or columns first ? indexing
  origin lower or upper ? a varying number of time steps for each file ?
  This is now all a breeze.
- Scan the files automatically to find values of coordinates, variables
  attributes, data indexing,...
- Load only subparts of data.
- Logs will ensure you are loading what you want to load.

And in general:

- Highly modulable, can be tailored to your needs.
- Fully documented.

As of now, this only supports NetCDF files out of the box. But the package can be
easily extended for other file formats. See the section 'Expanding the package'
of the documentation.

Only tested for linux, should work on other OS.

See examples/ for use cases.


Warning
-------

The code has not been extensively tested for all the possible use cases it
supports, and is evolving quickly.
I recommend you check thorougly in the logs that the correct files are opened,
and that the correct slices of data are taken from thoses files.
See the documentation on logging for more information.


Documentation
-------------

Documentation is available at `<http://data-loader.readthedocs.io>`__.


Requirements
------------

Data-loader requires python **>=3.7**. From this version, dictionaries
preserve the order in which keys are added.
The code heavily relies on this feature.
This could be avoided, but would require a fair bit of
refactoring.

Data-loader requires the following python packages::

  numpy

Optional dependencies::

  [NetCDF] NetCDF4 (for netcdf files, and time coordinate)
  [Mask] scipy (for some features of masked data)
  [Plots] matplotlib (for some of the plotting features)


Install
-------

To install, run::

  git clone https://github.com/Descanonges/data-loader.git & cd data-loader/
  pip install .

To add optional dependencies::

  pip install .[Feature name]
  # Feature name can be Mask, NetCDF, Plots

To remove::

  pip uninstall data-loader

The code is quickly evolving, it is recommended to upgrade it regurlarly::

  git pull
  pip install --upgrade .

Alternatively, the installation can be made with a symlink, so that any change
in the code is immediate, and only the git pull is necessary for upgrade.
I would recomment this for a fork::

  pip install -e .

