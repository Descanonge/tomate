
.. currentmodule:: data_loader.log

Logging
=======

This code make use of the logging built-in module to log out information.
Those logs are data-loader efforts to be accountable so that the user
can check it is doing everything right, but also to warn the user of
any potential error or mistake. Either way, they should not be ignored.

Most of that information comes at the 'INFO' level,
Warnings indicating something might not be well setup, log at the 'WARNING'
level.
Additional information, especially during the scanning process is output
at 'DEBUG'.


All logging related function are in :mod:`data_loader.log`.

Basic configuration
-------------------

Logging is activated whenever data_loader is first imported.
A top-level logger named 'data_loader' is setup by
:func:`set_logging_defaults`.
It outputs everything above (including) the 'INFO' level to stderr.
A logfile can be added by using :func:`add_file_handler`.

All 'data-loader' related logs can be limited to a certain level
by using :func:`set_logging_level`. Again, it is always advised to look
at 'INFO' outputs to check against potential errors.


Advanced configuration
----------------------

The basic configuration should supply sane defaults, but can be
configured more finely.
Being familiar with the `logging` module is advised though.

Logging is setup package-wide with the 'data_loader' logger.
The logger does not propagate to the root logger by default.
This is done to avoid tempering with the root logger configuration
that users might have already setup.
It can easily be setup to propagate again::

  log = data_loader.log.get_logger(``
  log.propagate = True

You might want to remove the package specific stderr handler present
by default.
Function are provided to remove specific handlers:
:func:`remove_handlers`, :func:`remove_stream_handlers`,
:func:`remove_file_handlers`.

The format of log message can be changed for all handlers conveniently using
:func:`change_format`.
Knowing the filename from whence the message originated can be useful, it can
be added with :func:`add_filename_message`.
