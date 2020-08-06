"""Stores metadata."""

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

    __setitem__ and pop will affect the VI.

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
        self._vi.set_attribute(k, self._name, v)
        super().__setitem__(k, v)

    def pop(self, k: str):
        self._vi.remove_pair(k, self._name)


class VariableAttributes(dict):
    """View into the VI for one variable.

    __setattr__, __setitem__, and pop will
    affect the VI.

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
        self._vi.set_attribute(self._name, name, value)
        self[name] = value

    def __setitem__(self, k: str, v: Any):
        self._vi.set_attribute(self._name, k, v)
        super().__setitem__(k, v)

    def pop(self, k: str):
        self._vi.remove_pair(self._name, k)


class VariablesInfo():
    """Gives various info about variables.

    General informations (infos) and variables
    specific information (attributes)
    are accessible as attributes.

    :param attributes: Variable specific information.
        {'variable name': {'attribute name': 'value', ...}, ...}
    :param infos: Any additional information to be stored as attributes.

    :attr _attributes: Dict[str, Dict[str, Any]]: Variables specific
        attributes. {'variable name': {'attribute name': 'value', ...}, ...}
    :attr _infos: Dict[str, Any]: General attributes.
    """

    def __init__(self, attributes: Dict[str, Dict[str, Any]] = None,
                 **infos: Any):
        if attributes is None:
            attributes = {}

        self._attributes = {}
        self._infos = {}

        for var, attrs in attributes.items():
            self.set_attributes_variable(var, **attrs)
        self.set_infos(**infos)

    @property
    def variables(self) -> List[str]:
        """List of variables names."""
        return list(self._attributes.keys())

    @property
    def attributes(self) -> List[str]:
        """List of attributes names."""
        out = {attr for var in self._attributes.values()
               for attr in var}
        return list(out)

    @property
    def infos(self) -> List[str]:
        """List of infos names."""
        return list(self._infos.keys())

    def __repr__(self):
        s = []
        s.append("Variables: {}".format(', '.join(self.variables)))
        s.append("Attributes: {}".format(', '.join(self.attributes)))
        s.append("Infos: {}".format(', '.join(self.infos)))
        return '\n'.join(s)

    def __getattribute__(self, item: str):
        """Make attributes and infos accessible as attributes."""
        get = super().__getattribute__

        # Allow to access self._attributes and self._infos
        # normally, useful when calling self.attributes
        # Does not allow use of methods in self.attributes
        if item in get('__dict__'):
            return get('__dict__')[item]

        if item in super().__getattribute__('attributes'):
            d = {var: values[item]
                 for var, values in get('_attributes').items()
                 if item in values}
            return Attribute(item, self, d)

        if item in get('_infos'):
            return get('_infos')[item]

        return get(item)

    def __iter__(self) -> Iterator[str]:
        """Enumerate over attributes attributes / variables pairs."""
        return iter([(var, attr) for var, values in self._attributes.items()
                     for attr in values])

    def __getitem__(self, item: str) -> VariableAttributes:
        """Return attributes for a variable.

        :param item: Variable
        :raises TypeError: Argument is not a string.
        :raises IndexError: Argument is not in variables.
        """
        if not isinstance(item, str):
            TypeError("Argument must be string")
        if item not in self.variables:
            IndexError(f"'{item}' not in variables")
        d = self._attributes[item]
        return VariableAttributes(item, self, d)

    def has(self, var: str, attr: str) -> bool:
        """Check if variable/attribute pair is in the VI."""
        out = (var in self._attributes
               and attr in self._attributes[var])
        return out

    def get_attribute(self, var: str, attr: str) -> Any:
        """Get attribute.

        :raises KeyError: Variable / attribute pair does not exists.
        """
        try:
            return self._attributes[var][attr]
        except KeyError:
            raise KeyError("'{}' attribute for variable '{}'"
                           " combination does not exists.".format(attr, var))

    def get_attribute_default(self, var: str, attr: str,
                              default: Any = None) -> Any:
        """Get attribute.

        If attribute is not defined for this variable,
        return `default`.
        """
        try:
            return self.get_attribute(var, attr)
        except KeyError:
            return default

    def get_attribute_param(self, var: str, attr: str,
                            default: Any = None) -> Any:
        """Get attribute.

        Try 'attribute', then '_attribute', then `default`.
        """
        if self.has(var, attr):
            return self.get_attribute(var, attr)
        if self.has(var, f'_{attr}'):
            return self.get_attribute(var, f'_{attr}')
        return default

    def get_info(self, info: str) -> Any:
        """Get info."""
        return self._infos[info]

    def set_attribute(self, var: str, name: str, value: Any):
        """Set attribute for a variable."""
        if (name in self.__class__.__dict__.keys()
                or name in self.__dict__.keys()):
            log.warning("Ignoring attribute '%s' (name is reserved)", name)
        else:
            if var not in self._attributes:
                self._attributes[var] = {}
            self._attributes[var][name] = value

    def set_attributes(self, var: str, **attributes: Any):
        """Set multiple attributes for a variable. """
        for attr, value in attributes.items():
            self.set_attribute(var, attr, value)

    def set_attributes_default(self, var: str, **attributes: Any):
        """Set attributes if they are not already present."""
        for name, value in attributes.items():
            if not self.has(var, name):
                self.set_attribute(var, name, value)

    def set_attribute_variables(self, attribute: str, **values: Dict[str, Any]):
        """Set attribute for multiple variables.

        :param attribute: Attribute name.
        :param values: Attributes values for multiple variables.
        """
        for var, value in values.items():
            self.set_attribute(var, attribute, value)

    def set_info(self, name: str, value: Any):
        """Set info."""
        if name in self.__class__.__dict__.keys():
            log.warning("'%s' attribute is reserved.", name)
        else:
            self._infos[name] = value

    def set_infos(self, **infos: Any):
        """Set multiple infos."""
        for name, value in infos.items():
            self.set_info(name, value)

    def set_infos_default(self, **infos: Any):
        """Add infos if they are not already present."""
        for name, value in infos.items():
            if name not in self.infos:
                self.set_info(name, value)

    def remove_pair(self, var: str, attr: str):
        """Remove variable/attribute pair.

        :raises KeyError: If pair is not in VI.
        """
        if not self.has(var, attr):
            raise KeyError("Pair not in VI.")
        self._attributes[var].pop(attr)
        if not self._attributes[var]:
            self._attributes.pop(var)

    def remove_variables(self, variables: Union[str, List[str]]):
        """Remove variables from VI. """
        if not isinstance(variables, list):
            variables = [variables]
        for var in variables:
            self._attributes.pop(var)

    def remove_attributes(self, attributes: Union[str, List[str]]):
        """Remove attribute."""
        if not isinstance(attributes, list):
            attributes = [attributes]

        for var in self.variables:
            for attr in attributes:
                if attr in self._attributes[var]:
                    self._attributes[var].pop(attr)
            if not self._attributes[var]:
                self._attributes.pop(var)

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
                vi.set_attr(var, attr, value_copy)

        for info, value in self._infos.items():
            try:
                value_copy = copy.deepcopy(value)
            except AttributeError:
                log.warning("Could not copy '%s' infos (type: %s)",
                            info, type(value))
                value_copy = value
            vi.set_info(info, value_copy)

        return vi
