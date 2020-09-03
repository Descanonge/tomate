
.. currentmodule:: tomate.log

Logging
=======

This code make use of the `logging` built-in module to log out information.
Those logs are Tomate best efforts to be accountable so that the user
can check it is doing everything right, but also to warn the user of
any potential error or mistake. Either way, they should not be ignored.

Logs comes at various levels:

DEBUG
  Less useful information, except if you are debugging
  your scripts. Used notably during scanning.
INFO
  Normal use feedback
WARNING
  Something might not be correctly setup and could cause
  issues down the line.
ERROR
  Something has gone horribly wrong. It happens to everyone. Those gremlins have
  the tendency to hide themselves just above error tracebacks, be sure to not
  miss them!

All logging related function are in :mod:`tomate.log`.

Basic configuration
-------------------

Logging is activated whenever tomate is first imported.
A top-level logger named 'tomate' is setup by
:func:`set_logging_defaults`.
It outputs everything above (including) the 'INFO' level to stderr.
A logfile can be added by using :func:`add_file_handler`.

All 'tomate' related logs can be limited to a certain level
by using :func:`set_logging_level`. Again, it is always advised to look
at 'INFO' outputs to check against potential errors. Especially when loading
data.


Advanced configuration
----------------------

The basic configuration should supply sane defaults, but can be
configured more finely.
Being familiar with the `logging` module is advised though.

Logging is setup package-wide with the 'tomate' logger.
The logger does not propagate to the root logger by default.
This is done to avoid tempering with the root logger configuration
that users might have already setup.
It can easily be setup to propagate again::

  log = tomate.log.get_logger()
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
