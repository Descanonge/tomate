"""Stores metadata on the variables."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import logging
import copy
from typing import Any, Dict, Iterator, List, Union


log = logging.getLogger(__name__)


class Attribute(dict):
    """View into the VI for one attribute.

    Allows to correctly set attributes.

    :param name: Name of the attribute.
    :param vi: Parent VI.

    :attr _name: str:
    :attr _vi: VariablesInfo:
    """
    def __init__(self, name: str, vi: 'VariablesInfo', kwargs: Any):
        self._name = name
        self._vi = vi
        super().__init__(**kwargs)

    def __setitem__(self, k: str, v: Any):
        self._vi.set_attrs(k, **{self._name: v})
        super().__setitem__(k, v)


class VariableAttributes(dict):
    """View into the VI for one variable.

    Allows to correctly set attributes.

    :param name: Name of the variable.
    :param vi: Parent VI.

    :attr _name: str:
    :attr _vi: VariablesInfo:
    """
    def __init__(self, name: str, vi: 'VariablesInfo', kwargs: Any):
        super().__setattr__('_name', name)
        super().__setattr__('_vi', vi)
        super().__init__(**kwargs)

    def __getattribute__(self, name: str):
        if name in self:
            return self[name]
        return super().__getattribute__(name)

    def __setattr__(self, name: str, value: Any):
        self._vi.set_attrs(self._name, **{name: value})
        self[name] = value


class VariablesInfo():
    """Gives various info about variables.

    General informations (infos) and variables
    specific information (attributes, abbreviated attrs)
    are accessible as attributes.

    :param attributes: Variable specific information.
        {'variable name': {'fullname': 'variable fullname', ...}, ...}
    :param infos: Any additional information to be stored as attributes.

    :attr variables: Set[str]: Variables names.
    :attr _attrs: Dict[str, Dict[str, Any]]: Variables specific
        attributes. Stored by attribute name then variable name.
    :attr _infos: Dict[str, Any]: General attributes.
    """

    def __init__(self, attributes: Dict[str, Dict[str, Any]] = None,
                 **infos: Any):
        if attributes is None:
            attributes = {}

        self.variables = set()
        self._attrs = {}
        self._infos = {}

        for var, attrs in attributes.items():
            self.set_attrs(var, **attrs)
        self.set_infos(**infos)

    @property
    def n(self) -> int:
        """Number of variables in the VI."""
        return len(self.variables)

    @property
    def attrs(self) -> List[str]:
        """List of attributes names."""
        return list(self._attrs.keys())

    @property
    def infos(self) -> List[str]:
        """List of infos names."""
        return list(self._infos.keys())

    def __repr__(self):
        s = []
        s.append("Variables: {}".format(', '.join(self.variables)))
        s.append("Attributes: {}".format(', '.join(self.attrs)))
        s.append("Infos: {}".format(', '.join(self.infos)))
        return '\n'.join(s)

    def __getattribute__(self, item: str):
        """Render attributes and infos accessible as attributes."""
        if item in super().__getattribute__('_attrs'):
            d = super().__getattribute__('_attrs')[item]
            return Attribute(item, self, d)
        if item in super().__getattribute__('_infos'):
            return super().__getattribute__('_infos')[item]
        return super().__getattribute__(item)

    def __iter__(self) -> Iterator[str]:
        """Enumerate over attributes attributes / variables pairs."""
        return iter([(var, attr) for attr, values in self._attrs.items()
                     for var in values])

    def __getitem__(self, item: str) -> VariableAttributes:
        """Return attributes for a variable.

        :param item: Variable

        :raises TypeError: Argument is not a string.
        :raises IndexError: Argument is not in variables.

        """
        if not isinstance(item, str):
            TypeError("Argument must be string.")
        if item in self.variables:
            d = {attr: values[item] for attr, values in self._attrs.items()
                 if item in values}
            return VariableAttributes(item, self, d)
        raise IndexError(f"'{item}' not in variables.")

    def get_attr(self, attr: str, var: str) -> Any:
        """Get attribute.

        :raises KeyError: Variable / attribute combinaison does not exists.
        """
        try:
            out = self._attrs[attr][var]
        except KeyError:
            raise KeyError("'{}' attribute for variable '{}'"
                           " combinaison does not exists.".format(attr, var))
        return out

    def get_attr_safe(self, attr: str, var: str, default: Any = None) -> Any:
        """Get attribute.

        If attribute is not defined for this variable,
        return default.
        """
        try:
            value = self.get_attr(attr, var)
        except KeyError:
            value = default
        return value

    def get_info(self, info: str) -> Any:
        """Get info."""
        return self._infos[info]

    def set_attrs(self, var: str, **attrs: Any):
        """Set attributes for a variable.

        :param var: Variable name.
        :param attrs: Attributes values.
        """
        self.variables.add(var)
        for attr, value in attrs.items():
            if attr in self.__class__.__dict__.keys():
                log.warning("'%s' attribute is reserved.", attr)
            else:
                if attr not in self._attrs:
                    self._attrs[attr] = {}
                self._attrs[attr][var] = value

    def set_attr_variables(self, attr: str, **values: Dict[str, Any]):
        """Set attribute for multiple variables.

        :param attr: Attribute name.
        :param values: Attributes values for multiple variables.
        """
        for var, value in values.items():
            self.set_attrs(var, **{attr: value})

    def set_infos(self, **infos: Any):
        """Add infos."""
        for name, value in infos.items():
            if name in self.__class__.__dict__.keys():
                log.warning("'%s' attribute is reserved.", name)
            else:
                self._infos[name] = value

    def remove_variables(self, variables: Union[str, List[str]]):
        """Remove variables from vi.

        :param variables: Variables to remove.
        """
        if not isinstance(variables, list):
            variables = [variables]

        for attr in self.attrs:
            for var in variables:
                self._attrs[attr].pop(var)
        for var in variables:
            self.var.remove(var)

    def remove_attributes(self, attributes: Union[str, List[str]]):
        """Remove attribute.

        :param attributes: Attributes to remove.
        """

        if not isinstance(attributes, list):
            attributes = [attributes]

        for attr in attributes:
            self._attrs.pop(attr)

    def copy(self) -> "VariablesInfo":
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
