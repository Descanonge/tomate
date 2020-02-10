
Logging
=======

This code make use of the logging built-in module to log information.
A global Logger is set when importing the package, and all submodules
inherits its configuration.

By default, the parent logger logs into the stdout at the 'INFO' level.
Info includes most notably information on how the data is loaded (the
size of the data allocated, the file being opened, what is taken in that
file, where it is put,...).
I strongly advise to look carefully at those logs to check that the package
is working as intended.
More information on the scanning of coordinates can be found at the
'DEBUG' level.

Some aspects of the logging can be modified using functions from the
:mod:`log<data_loader.log>` module.
More experienced users can directly modify the global logger, whose
name is 'data_loader'.

If you really don't want those in your terminal ((ง •̀_•́)ง), use the following code::
