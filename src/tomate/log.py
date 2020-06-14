"""Logging functions."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import sys
import logging


def get_logger():
    """Return top-level package logger."""
    return logging.getLogger('tomate')


def set_logging_level(level: str = 'INFO'):
    """Set package-wide logging level.

    :param level: {'debug', 'info', 'warn', 'error', 'critical'}
         Not case sensitive.
    """
    log = get_logger()
    level_num = getattr(logging, level.upper())
    log.setLevel(level_num)


def set_logging_defaults():
    """Set default configuration for logging.

    Set up basicConfig if not already.
    For top-level package logger:

        - Remove present handlers
        - Set logging level to Info
        - No propagation
        - Add stderr stream handler
    """
    logging.basicConfig()

    log = get_logger()
    remove_handlers()
    log.setLevel(logging.INFO)
    log.propagate = False

    add_stream_handler()


def add_stream_handler(stream=None, level: str = None):
    """Add stream handler.

    :param stream: Stream to use. If None, stderr is used.
        A string can also be specified ('stderr' or 'stdout')
    :param level: [opt] Level for this handler.
        If None, all messages are processed.
    """
    log = get_logger()

    if stream == 'stdout':
        stream = sys.stdout
    elif stream == 'stderr':
        stream = sys.stderr
    handler = logging.StreamHandler(stream)
    formatter = logging.Formatter(fmt='%(levelname)s:tomate:%(message)s')
    handler.setFormatter(formatter)

    if level is not None:
        handler.setLevel(getattr(logging, level.upper()))

    log.addHandler(handler)


def add_file_handler(filename: str, mode: str = 'w', level: str = None):
    """Add file handler to log to disk.

    :param mode: Mode to use to open file.
    :param level: [opt] Level for this handler.
        If None, all messages are processed.
    """
    log = get_logger()
    handler = logging.FileHandler(filename, mode=mode)
    formatter = logging.Formatter(fmt='%(levelname)s:tomate:%(message)s')
    handler.setFormatter(formatter)

    if level is not None:
        handler.setLevel(getattr(logging, level.upper()))

    log.addHandler(handler)


def remove_stream_handlers():
    """Remove all stream handler from package logger."""
    log = get_logger()
    handlers = log.handlers
    for handler in handlers:
        if isinstance(handler, logging.StreamHandler):
            log.removeHandler(handler)


def remove_file_handlers():
    """Remove all file handler from package logger."""
    log = get_logger()
    handlers = log.handlers
    for handler in handlers:
        if isinstance(handler, logging.FileHandler):
            log.removeHandler(handler)


def change_format(fmt: str):
    """Change format on all handlers."""
    log = get_logger()
    formatter = logging.Formatter(fmt)
    for handler in log.handlers:
        handler.setFormatter(formatter)


def add_filename_message():
    """Add filename to message."""
    change_format('%(levelname)s:%(name)s:%(message)s')


def remove_handlers():
    """Remove all handlers from package logger."""
    log = get_logger()
    log.handlers.clear()
