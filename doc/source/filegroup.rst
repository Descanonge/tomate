
Filegroups
==========

A data object contains one or more
:class:`FilegroupLoad<data_loader.filegroup.filegroup_load.FilegroupLoad>`.
This object manages a couple of tasks. It first does the scanning of all
datafiles to find the various coordinates values.
It also manages the loading of the data (actually opening the files).

The scanning functionalities are written in the
:class:`FilegroupScan<data_loader.filegroup.filegroup_scan.FilegroupScan>`.
The loading functions are specified in the abstract class
:class:`FilegroupLoad<data_loader.filegroup.filegroup_load.FilegroupLoad>`.
This class is to be subclassed, to write the file-format specific functions.


Scanning
--------


Loading
-------
