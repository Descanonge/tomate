Data Loader
===========

Load data arranged in various way on disk.

**This is still in alpha, use at your own risk !**


Features
--------

- Load data that spans multiple files and comes from different sources easily.
- Scan the files automatically to find values of coordinates.
- Manage the data once loaded, and keep information about its variables at
  hand.
- Use and create convenience function for analysis, plotting,...
- Highly modulable, can be tailored to your needs.

As of now, this only supports NetCDF files out of the box. But the package can be
easily extended for other file formats.

Only tested for linux, should work on other OS.

See examples/ for use cases.


TODO
----

The code is still in alpha, and has to be considered unsafe. I recommend you
check thorougly that the correct files are opened, and that the correct slices
of data are taken from thoses files. Info messages are used to this end.
If you really don't want those in your terminal ((ง •̀_•́)ง), use the following code::

  from data_loader import log
  log.set_logging("WARN")

  # or
  log.set_file_log("log.txt", no_stdout=True)

See the documentation on logging for more information.


Documentation
-------------

Documentation is available at `<http://data-loader.readthedocs.io>`__.


Requirements
------------

This requires the following python packages::

  numpy

Optional dependencies::

  [Mask] scipy (for masked data)
  [NetCDF] NetCDF4 (for netcdf files)


Install
-------

To install, run::

  git clone https://github.com/Descanonges/data-loader.git & cd data-loader/
  pip install .

To add optional dependencies::

  pip install .[Feature name]
  # Feature name can be Mask, NetCDF

To remove::

  pip uninstall data-loader

The code is quickly evolving, it is recommended to upgrade it regurlarly::

  git pull
  pip install --upgrade .

Alternatively, the installation can be made with a symlink, so that any change
in the code is immediate, and only the git pull is necessary for upgrade::

  pip install -e .

