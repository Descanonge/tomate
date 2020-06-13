
# Tomate

> **To**ol to **M**anipulate and **A**ggrega**te** data

<div align="left">

[![PyPI version](https://badge.fury.io/py/tomate-data.svg)](https://pypi.org/project/tomate-data)
[![Release status](https://img.shields.io/github/v/release/Descanonge/tomate)](https://github.com/Descanonge/tomate/releases)

</div>

Tomate is a Python package that provides ways to manipulate data
under the form of a multi-dimensional array.
It manages multiples variables, as well as the coordinates along
which the data varies.
It also provides multiple convenience functions to retrieve
subparts of the data, do computations, or plot the data.

The data can be retrieved from disk, where it can be arranged
in multiple ways and formats.
Information on the data, such as variable attributes,
or coordinates values can be retrieved automatically.


## Features

For data in memory:
- Keep information about the data, the variables, the coordinates.
  All this information is in sync with the data.
- Select subparts of data easily.
- Use and create convenience function for analysis, plotting,...

For data on disk:
- Load data that spans multiple files and comes from different sources easily.
  Different file format ? different structure: rows or columns first ? indexing
  origin lower or upper ? a varying number of time steps for each file ?
  This is now all a breeze !
- Scan the files automatically to find values of coordinates, variables
  attributes, data indexing,...
- Load only subparts of data.
- Logs will ensure you are loading what you want to load.

And in general:
- Highly modulable, can be tailored to your needs.
- Fully documented.

As of now, this only supports NetCDF files out of the box. But the package can be
easily extended for other file formats. See the section
['Expanding the package'](https://tomate.readthedocs.io/en/latest/expanding.html)
of the documentation.

Only tested for linux, should work on other OS.

See [examples] for use cases.


## Warning

The code has not been extensively tested for all the possible use cases it
supports, and is evolving quickly.
I recommend you check thorougly in the logs that the correct files are opened,
and that the correct slices of data are taken from thoses files.
See the [documentation on logging](https://tomate.readthedocs.io/en/latest/log.html)
for more information.

Features supplied in 'data_write', that allow to save a database information in
a json file to avoid re-scanning it each time, is to be considered very experimental.


## Documentation

Documentation is available online at [ReadTheDocs](https://tomate.readthedocs.io)


## Requirements

Tomate requires python **>=3.7**. From this version, dictionaries
preserve the order in which keys are added. The code heavily relies on this feature.
This could be avoided, but would require a fair bit of refactoring.

Tomate requires the following python packages:
  - numpy

Optional dependencies:
  - [time] [cftime>=1.1.3](https://github.com/Unidata/cftime) -
    To manage dates in time coordinates
  - [netcdf] [netcdf4-python](https://github.com/Unidata/netcdf4-python) -
    To open netCDF4 files
  - [plot] matplotlib - To create plots easily
  - [compute] scipy - To do various computation on the data


## Install

The package is distributed through PyPI.
To install, run:

``` sh
pip install tomate-data
```

To add optional dependencies:

``` sh
pip install tomate-data [feature name]
```

Feature name can be Time, NetCDF, Plot, Compute. 

The code is evolving quickly, it is recommended to upgrade it regurlarly:

``` sh
pip install --upgrade tomate-data
```

Or to even install it directly from the development branch.
This will place the package files in `./src`, from where you just have to do a `git pull`
to update from the latest commit:

``` sh
pip install -e git+https://github.com/Descanonge/tomate.git@develop#egg=tomate-data
```


[examples]: examples
