"""Logging functions."""

import logging


def set_logging(level='INFO'):
    """Set package-wide logging level.

    Parameters
    ----------
    level: {'debug', 'info', 'warn', 'error', 'critical'}
         Not case sensitive.
    """
    level_num = getattr(logging, level.upper())
    logging.getLogger('data_loader').setLevel(level_num)


def set_file_log(filename: str, no_stdout=False, level=None):
    """Redirect output to file.

    Parameters
    ----------
    filename: str
        File to output log.
    no_stdout: bool
        Disable logging to the stdout.
    """
    logger = logging.getLogger('data_loader')
    handler = logging.FileHandler(filename, mode='w')

    if level is not None:
        level_num = getattr(logging, level.upper())
        handler.setLevel(level_num)

    logger.addHandler(handler)

    if no_stdout:
        logger.propagate = False


logging.basicConfig()
