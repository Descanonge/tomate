"""Logging functions."""

import logging


def set_logging(level='INFO'):
    """Set package-wide logging level.

    Parameters
    ----------
    level: str
         DEBUG | INFO | WARN | ERROR | CRITICAL
         Not case sensitive
    """
    level_num = getattr(logging, level.upper())
    logging.getLogger('data_loader').setLevel(level_num)


def set_file_log(filename: str, no_stdout=False):
    """Redirect output to file."""
    logger = logging.getLogger('data_loader')
    handler = logging.FileHandler(filename, mode='w')
    logger.addHandler(handler)

    if no_stdout:
        logger.propagate = False


logging.basicConfig()
