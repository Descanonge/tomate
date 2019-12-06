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
- Highly modulable, can be tailored to your needs.
- NetCDF files support, with masked data, and land mask.

As of now, this only supports NetCDF files out of the box. But the package can be
easily extended for other file formats.

Support Linux only. Other platforms incoming !

See examples/ for use cases.


TODO
----

The code is still in alpha, and has to be considered unsafe. I recommend you
check thorougly that the correct files are opened, and that the correct slices
of data are taken from thoses files.
Info messages are used to this end for now, and will be limited to debuging in
the future, when the code will have been more closely reviewed. If you really
don't want those messages ((ง •̀_•́)ง), use the following code::

  from data_loader import set_logging
  set_logging("WARN")

More logging information is also to come in the near future.


Requirements
------------

This requires the following python packages::

  numpy
  scipy
  netCDF4


Install
-------

To install, run::

  git clone https://github.com/Descanonges/data-loader.git & cd data-loader/
  pip install .

To remove::

  pip uninstall data-loader

The code is quickly evolving, it is recommended to upgrade it regurlarly::

  git pull
  pip install --upgrade .

Alternatively, the installation can be made with a symlink, so that any change
in the code is immediate, and only the git pull is necessary for upgrade::

  pip install -e .


Documentation
-------------

Documentation is available at `<http://data-loader.readthedocs.io>`__.
