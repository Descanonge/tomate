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

As of now, this supports NetCDF files out of the box. But the package can be
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
don't want those messages ((ง •̀_•́)ง), launch your python interpreter with the
option `--log-level=WARN`.
More logging information is also to come in the near future.

If data coming from different sources does not have the same range, a warning
is issued. At term, the code should only load overlaping data, however this is
still buggy. I recommend that you avoid this warning for now.

Requirements
------------

This requires the following python packages::

  numpy
  netCDF4
  matplotlib
  shapely

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

Documentation is on its way, though the code itself is already well commented.
An API reference can be build with sphinx.
In doc/::

   sphinx-apidoc -fe -o source/references ../data_loader
