"""Stores metadata on the variables."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


import logging
import copy


log = logging.getLogger(__name__)



class Attribute(dict):
    """View into the VI.

    Allows to correctly set attributes.

    Parameters:
    -----------
    name: str
        Name of the attribute
    vi: VariablesInfo

    Attributes
    ----------
    _name: str
    _vi: VariablesInfo
    """
    def __init__(self, name, vi, kwargs):
        self._name = name
        self._vi = vi
        super().__init__(**kwargs)

    def __setitem__(self, k, v):
        self._vi.set_attrs(k, **{self._name: v})
        super().__setitem__(k, v)


class VariablesAttributes(dict):
    """View into the VI.

    Allows to correctly set attributes.
    """
    def __init__(self, name: str, vi: "VariablesInfo", kwargs):
        super().__setattr__('_name', name)
        super().__setattr__('_vi', vi)
        super().__init__(**kwargs)

    def __getattribute__(self, name: str):
        if name in self:
            return self[name]
        return super().__getattribute__(name)

    def __setattr__(self, name, value):
        self._vi.set_attrs(self._name, **{name: value})
        self[name] = value


class VariablesInfo():
    """Gives various info about variables.

    General informations (infos) and variables
    specific information (attributes, abbreviated attrs)
    are accessible as attributes.
    Variable specific informations are stored as IterDict.

    Parameters
    ----------
    attributes: Dict[str, Dict[str: Any]]
        Variable specific information.
        {'variable name': {'fullname': 'variable fullname', ...}, ...}
    infos
        Any additional information to be stored as attributes.

    Attributes
    ----------
    var: Set[var]
        Variables names
    _attrs: Dict[attribute: str, Dict[variable: str, Any]]
    _infos: Dict[info: str, Any]
    """

    def __init__(self, attributes=None, **infos):
        if attributes is None:
            attributes = {}

        self.var = set()
        self._attrs = {}
        self._infos = {}

        for var, attrs in attributes.items():
            self.set_attrs(var, **attrs)
        self.set_infos(**infos)

    @property
    def n(self):
        """Number of variables in the VI."""
        return len(self.var)

    @property
    def attrs(self):
        """List of attributes names."""
        return list(self._attrs.keys())

    @property
    def infos(self):
        """List of infos names."""
        return list(self._infos.keys())

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
            d = super().__getattribute__('_attrs')[item]
            return Attribute(item, self, d)
        if item in super().__getattribute__('_infos'):
            return super().__getattribute__('_infos')[item]
        return super().__getattribute__(item)

    def __iter__(self):
        """Enumerate over var."""
        return iter(self.var)

    def __getitem__(self, item):
        """Return attributes for a variable.

        Parameters
        ----------
        item: str
            Variable

        Raises
        ------
        TypeError
            Argument is not a string.
        IndexError
            Argument is not in variables.

        """
        if not isinstance(item, str):
            TypeError("Argument must be string.")
        if item in self.var:
            d = {attr: values[item] for attr, values in self._attrs.items()}
            return VariablesAttributes(item, self, d)
        raise IndexError("'%s' not in variables." % item)

    def get_attr(self, attr, var):
        """Get attribute."""
        return self._attrs[attr][var]

    def get_attr_safe(self, attr, var, default=None):
        """Get attribute.

        If attribute is not defined for this variable,
        return default.
        """
        value = default
        if attr in self._attrs:
            value = self._attrs[attr][var]
        return value

    def get_info(self, info):
        """Get info."""
        return self._infos[info]

    def set_attrs(self, var, **attrs):
        """Set attributes for a variable.

        Parameters
        ----------
        var: str
            Variable name.
        attrs: Any
            Attributes values.
        """
        self.var.add(var)
        for attr, value in attrs.items():
            if attr in self.__class__.__dict__.keys():
                log.warning("'%s' attribute is reserved.", attr)
            else:
                if attr not in self._attrs:
                    self._attrs[attr] = {}
                self._attrs[attr][var] = value

    def set_attr_variables(self, attr, **values):
        """Set attribute for multiple variables.

        Parameters
        ----------
        attr: str
            Attribute name.
        values: Any
            Attributes values for multiple variables.
        """
        for var, value in values.items():
            self.set_attrs(var, **{attr: value})

    def set_infos(self, **infos):
        """Add infos."""
        for name, value in infos.items():
            if name in self.__class__.__dict__.keys():
                log.warning("'%s' attribute is reserved.", name)
            else:
                self._infos[name] = value

    def remove_variables(self, variables):
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
        for var in variables:
            self.var.remove(var)

    def remove_attributes(self, attributes):
        """Remove attribute.

        Parameters
        ----------
        attributes: str or List[str]
            Attributes to remove.
        """

        if not isinstance(attributes, list):
            attributes = [attributes]

        for attr in attributes:
            self._attrs.pop(attr)

    def copy(self):
        """Return copy of self."""
        vi = VariablesInfo()

        for attr, values in self._attrs.items():
            for var, value in values.items():
                try:
                    value_copy = copy.deepcopy(value)
                except AttributeError:
                    log.warning("Could not copy '%s' attribute (type: %s)",
                                attr, type(value))
                    value_copy = value
                vi.set_attrs(var, **{attr: value_copy})

        for info, value in self._infos.items():
            try:
                value_copy = copy.deepcopy(value)
            except AttributeError:
                log.warning("Could not copy '%s' infos (type: %s)",
                            info, type(value))
                value_copy = value
            vi.set_infos(**{info: value_copy})

        return vi
