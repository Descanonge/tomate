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
import tomate

# -- Project information -----------------------------------------------------

project = 'Tomate'
copyright = '2020, Clément Haëck'
author = 'Clément Haëck'

# The full version, including alpha/beta/rc tags
release = tomate.__version__

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
autosummary_generate = False
always_document_param_types = True


# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', '_ext', 'Thumbs.db', '.DS_Store',
                    '_ref_combine', '_ref_override']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.

# html_theme_path = [sphinx_readable_theme.get_html_theme_path()]
html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'navigation_depth': 3
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ['_static']


def sort_sections(app, what, name, obj, options, lines):
    """Sort.

    In the order:
        First section
        Parameters
        Returns
        Other sections.

    Functions arguments are sorted.
    """
    import re
    import inspect

    if isinstance(obj, tomate.filegroup.scanner.ScannerCS):
        obj = obj.func

    def add(linelist, i):
        linelist.append(lines[i])
        i += 1
        while i < len(lines) and lines[i].startswith('    '):
            linelist.append(lines[i])
            i += 1
        return i

    return_keys = [':returns', ':return']
    section_keys = ['.. rubric::', '.. seealso::']

    rgx = '^:param ([^:]*)'

    parameters = {}
    attributes = []
    types = []
    returns = []
    return_type = []
    raises = []
    sections = []
    current_sec = []
    i = 0
    while i < len(lines):
        m = re.search(rgx, lines[i])
        if m:
            argname = m.group(1)
            parameters[argname] = []
            i = add(parameters[argname], i)
        elif any([lines[i].startswith(k) for k in return_keys]):
            i = add(returns, i)
        elif lines[i].startswith(':attr'):
            attr = []
            i = add(attr, i)
            attributes.append(attr)
        elif lines[i].startswith(':rtype'):
            i = add(return_type, i)
        elif lines[i].startswith(':type '):
            i = add(types, i)
        elif lines[i].startswith(':raises '):
            i = add(raises, i)
        elif any([lines[i].startswith(k) for k in section_keys]):
            sections.append(current_sec)
            current_sec = [lines[i]]
            i += 1
        else:
            current_sec.append(lines[i])
            i += 1
    sections.append(current_sec)

    lines.clear()
    lines += sections[0]

    try:
        order = inspect.signature(obj).parameters.keys()
    except (ValueError, TypeError):
        order = parameters.keys()
    for argname in order:
        if argname in parameters:
            lines += parameters[argname]
    lines += types

    attrs = dict([get_attr_lines(attr) for attr in attributes])

    if attrs:
        lines += ['']
        attrs_names = list(attrs.keys())
        attrs_names.sort()
        for name in attrs_names:
            lines += attrs[name]
    if return_type:
        lines += [''] + return_type
    if returns:
        lines += [''] + returns
    if raises:
        lines += [''] + raises
    for sec in sections[1:]:
        lines += [''] + sec


def get_attr_lines(lines):
    text = ''.join(lines).strip()
    elts = text.split(':')
    name = elts[1].strip()[5:]
    tp = elts[2].strip()
    desc = ' '.join(elts[3:])

    lines_ = ['.. attribute:: ' + name,
              '    :type: ' + tp,
              '',
              '    ' + desc]
    return name, lines_


def move_opt(app, what, name, obj, options, lines):
    """Add optional to type if specified.

    An optional argument is specified with :param ...: [opt] ...
    """
    import re
    rgx = r':param ([^:]*):\s?(\[opt\]?)'

    for i, line in enumerate(lines):
        m = re.search(rgx, line)
        if m and m.group(2) is not None:
            lines[i] = line[:m.start(2)] + line[m.end(2)+1:]
            argname = m.group(1)
            for j, line_ in enumerate(lines):
                if line_.startswith(":type {}:".format(argname)):
                    lines[j] = line_ + ", optional"
                    break


def fix_scanner_docstring(app, what, name, obj, options, lines):
    if isinstance(obj, tomate.filegroup.scanner.ScannerCS):
        if not any(line.startswith(':returns:') for line in lines):
            lines += [":returns: {}".format(', '.join(obj.elts)), ""]


def debug(app, what, name, obj, options, lines):
    # if 'Coord' in name:
    if name.endswith('nc.scan_in_file'):
        print(name)
        print('\n'.join(lines))
        print()
        print()


def setup(app):
    app.connect('autodoc-process-docstring', fix_scanner_docstring)
    app.connect('autodoc-process-docstring', move_opt)
    app.connect('autodoc-process-docstring', sort_sections)
    # app.connect('autodoc-process-docstring', debug)
