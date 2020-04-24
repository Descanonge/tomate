# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys

import sphinx_rtd_theme
sys.path.insert(0, os.path.abspath('../'))
sys.path.append(os.path.abspath("./_ext/sphinx-autodoc-typehints"))
import data_loader

# -- Project information -----------------------------------------------------

project = 'Data Loader'
copyright = '2019, Clément Haëck'
author = 'Clément Haëck'

# The full version, including alpha/beta/rc tags
release = data_loader.__version__

master_doc = 'index'

# -- General configuration ---------------------------------------------------
# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx_rtd_theme',
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.coverage',
    'sphinx.ext.napoleon',
    'sphinx_autodoc_typehints',
]

napoleon_use_param = True
autosummary_generate = True
always_document_param_types = True


# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', '_ext', 'Thumbs.db', '.DS_Store',
                    'data_loader.rst']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.

# html_theme_path = [sphinx_readable_theme.get_html_theme_path()]
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ['_static']

