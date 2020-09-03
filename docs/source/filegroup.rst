
.. currentmodule:: tomate.filegroup

Filegroups
----------

A data object contains one or more filegroup.
This object manages a couple of tasks. First it does the scanning of all
datafiles to find the various coordinates values.
It also manages the loading of the data (actually opening the files).

The scanning functionalities are written in the
:class:`FilegroupScan<filegroup_scan.FilegroupScan>`.
The loading functions are specified in the class
:class:`FilegroupLoad<filegroup_load.FilegroupLoad>`,
subclass of FilegroupScan.
The latter is to be subclassed for file-format specific functions.

.. seealso::

   :doc:`scanning` for more information on the scanning process
