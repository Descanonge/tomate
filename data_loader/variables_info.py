"""Stores metadata on the variables."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


import logging
import copy

from data_loader.iter_dict import IterDict


log = logging.getLogger(__name__)


class VariablesInfo():
    """Gives various info about variables.

    General informations (infos) and variables
    specific information (attributes, abbreviated attrs)
    are accessible as attributes.
    Variable specific informations are stored as IterDict.

    Parameters
    ----------
    variables: List[str]
        Variables names.
    attributes: Dict[str, Dict[str: Any]]
        Variable specific information.
        {'variable name': {'fullname': 'variable fullname', ...}, ...}
    infos
        Any additional information to be stored as attributes.

    Attributes
    ----------
    var: List[str]
        Variables names
    n: int
        Number of variables
    'attrs': Dict[attribute: str, IterDict[variable: str, Any]]
    'infos': Dict[info: str, Any]
    """

    def __init__(self, variables=None, attributes=None, **infos):
        if variables is None:
            variables = []
        if attributes is None:
            attributes = {}

        self.var = tuple(variables)
        self.n = len(variables)

        self._attrs = {}
        self._infos = {}

        for var, attrs in attributes.items():
            self.add_attrs_per_variable(var, attrs)
        self.add_infos(**infos)

    def __str__(self):
        s = []
        s.append("Variables: %s" % ', '.join(self.var))
        s.append("Attributes: %s" % ', '.join(self.attrs))
        s.append("Infos: %s" % ', '.join(self.infos))
        return '\n'.join(s)

    def __repr__(self):
        return '\n'.join([super().__repr__(), str(self)])

    def __getattribute__(self, item):
        """Render attributes and infos accessible as attributes."""
        if item in super().__getattribute__('_attrs'):
            return super().__getattribute__('_attrs')[item]
        if item in super().__getattribute__('_infos'):
            return super().__getattribute__('_infos')[item]
        return super().__getattribute__(item)

    def __iter__(self):
        """Enumerate over var."""
        return iter(self.var)

    def __getitem__(self, item):
        """Return VariableInfo slice.

        Parameters
        ----------
        item: str
            Variable or attribute

        Returns
        -------
        vi: Dict[Any]
        """
        if item in self.var:
            return {name: attrs[item] for name, attrs in self._attrs}
        if item in self.attrs:
            return self._attrs[item]
        raise IndexError("'%s' not in variables or attributes." % item)

    def print_variable(self, variable, print_none=False):
        """Print all information about a variable."""
        s = []
        s.append("Variable: %s" % variable)
        for attr in self.attrs:
            value = self.get_attr(attr, variable)
            if value is not None or print_none:
                s.append("%s: %s" % (attr, str(value)))
        return '\n'.join(s)

    def get_attr(self, attr, var):
        """Get attribute."""
        return self._attrs[attr][var]

    def get_attr_safe(self, attr, var, default=None):
        """Get attribute."""
        value = None
        if attr in self._attrs:
            value = self._attrs[attr][var]
        if value is None:
            value = default
        return value

    def get_info(self, info):
        """Get info."""
        return self._infos[info]

    @property
    def attrs(self):
        """Get list of attributes."""
        return list(self._attrs.keys())

    @property
    def infos(self):
        """Get list of infos."""
        return list(self._infos.keys())

    def copy(self):
        """Copy this instance."""
        var_list = copy.copy(self.var)

        attrs = {var: {} for var in var_list}
        for attr, values in self._attrs.items():
            for var, value in values.items():
                try:
                    value_copy = copy.deepcopy(value)
                except AttributeError:
                    log.warning("Could not copy '%s' attribute (value: %s)",
                                attr, value)
                    value_copy = value
                attrs[var][attr] = value_copy

        infos = {}
        for info, value in self._infos.items():
            try:
                value_copy = copy.deepcopy(value)
            except AttributeError:
                value_copy = value
            infos[info] = value

        vi = VariablesInfo(var_list, attrs, **infos)

        return vi

    def add_attr(self, attr, values=None):
        """Add attribute.

        Parameters
        ----------
        attr: str
            Attribute name.
        values: Dict[variable: str, Any]
            Values for some or all variables.
            Variables not specified will be filled with None.
        """
        if attr in self.__class__.__dict__.keys():
            log.warning("'%s' attribute is reserved.", attr)
        else:
            if attr not in self.attrs:
                self._attrs[attr] = IterDict(dict(zip(self.var, [None]*self.n)))

            if values is None:
                values = {}
            self._attrs[attr].update(values)

    def add_attrs_per_variable(self, var, attrs):
        """Add attributes for a single variable.

        Parameters
        ----------
        var: str
            Variable name.
        attrs: Dict
            Attributes name and values.
            {'attribute name': value}
        """
        for k, z in attrs.items():
            self.add_attr(k, {var: z})

    def add_variable(self, variable, **attrs):
        """Add a variable with corresponding attributes.

        Parameters
        ----------
        variable: str
            Variable name.
        attrs:
            Attributes name and values.
            If an attribute present in the VI is not provided,
            it is filled with None for the new variable.
        """
        if not attrs:
            attrs = {}
        var_list = list(self.var) + [variable]
        self.var = tuple(var_list)

        for attr in self.attrs:
            self._attrs[attr][variable] = None

        self.n += 1
        self.add_attrs_per_variable(variable, attrs)

    def pop_variables(self, variables):
        """Remove variables from vi.

        Parameters
        ----------
        variables: str or List[str]
            Variables to remove.
        """
        if not isinstance(variables, list):
            variables = [variables]

        for attr in self.attrs:
            for var in variables:
                self._attrs[attr].pop(var)

        var_list = list(self.var)
        for v in variables:
            var_list.remove(v)
            self.n -= 1
        self.var = tuple(var_list)

    def remove_attr(self, attr):
        """Remove attribute."""
        self._attrs.pop(attr)

    def add_infos(self, **infos):
        """Add infos."""
        for name, value in infos.items():
            if name in self.__class__.__dict__.keys():
                log.warning("'%s' attribute is reserved.", name)
            else:
                self._infos[name] = value
