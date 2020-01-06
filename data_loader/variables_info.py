"""Stores metadata on the variables."""

import copy

from data_loader.iter_dict import IterDict


class VariablesInfo():
    """Gives various info about variables.

    General informations (kwargs) and variables
    specific information (infos) are accessible as attributes.
    Variable specific informations are stored as IterDict.

    Parameters
    ----------
    variables: List[str]
        Variables names.
    infos: Dict[str, Dict[str: Any]]
        Variable specific information / attribute.
        {'variable name': {'fullname': 'variable fullname', ...}, ...}
    kwargs
        Any additional information to be stored as attributes.

    Attributes
    ----------
    var: List[str]
        Variables names
    idx: Dict[name: str, int]
        Index of variables in the data.
    n: int
        Number of variables
    'infos': IterDict[variable: str, Any]
    'kwargs': Any
    """

    def __init__(self, variables=None, infos=None, **kwargs):
        # Add the var and idx attributes
        if variables is None:
            variables = []
        if infos is None:
            infos = {}

        self.var = tuple(variables)
        self.idx = IterDict({k: i for i, k in enumerate(variables)})
        self.n = len(variables)

        self._infos = []
        for var, info in infos.items():
            self.add_infos_per_variable(var, **info)

        # TODO: No dynamic arguments
        # Make a __getattribute__ to access _infos and _kwargs
        # who would now contain the values as well
        # we would avoid messing with __dict__ all the time
        self._kwargs = []
        self.add_kwargs(**kwargs)

    def __str__(self):
        s = []
        s.append("Variables: %s" % ', '.join(self.var))
        s.append("Infos: %s" % ', '.join(self.infos))
        s.append("Other attributes: %s" % ', '.join(self.kwargs))
        return '\n'.join(s)

    def print_variable(self, variable, print_none=False):
        """Print all information about a variable."""
        s = []
        s.append("Variable: %s" % variable)
        for info in self.infos:
            value = self.get_info(info, variable)
            if value is not None:
                s.append("%s: %s" % (info, str(value)))
        return '\n'.join(s)

    def __iter__(self):
        # TODO: enumerate over idx ?
        """Enumerate over var."""
        return enumerate(self.var)

    def __getitem__(self, item):
        """Return VariableInfo slice.

        Parameters
        ----------
        item: str, List[str], slice of str, int, List[int], slice of int

        Returns
        -------
        vi: VariablesInfo
        """
        keys = self.idx[item]
        if not isinstance(keys, list):
            keys = [keys]

        var = [self.var[i] for i in keys]

        infos = {}
        for key in self._infos:
            value = getattr(self, key).copy()
            for name in self.var:
                if name not in var:
                    value.pop(name)
            infos.update({key: value})

        kwargs = {k: self.__dict__[k] for k in self._kwargs}

        vi = VariablesInfo(var, {}, **kwargs)

        for name, info in infos.items():
            vi.add_info(name, info)

        return vi

    @property
    def infos(self):
        """Get list of infos."""
        return self._infos

    @property
    def kwargs(self):
        """Get list of kwargs."""
        return self._kwargs

    def copy(self):
        """Copy this instance."""
        var_list = copy.copy(self.var)

        infos = {}
        for key in self._infos:
            value = getattr(self, key).copy()
            infos.update({key: value})

        kwargs = {}
        for key in self._kwargs:
            value = getattr(self, key)
            try:
                value = copy.copy(value)
            except AttributeError:
                pass
            kwargs.update({key: value})

        vi = VariablesInfo(var_list, {}, **kwargs)

        for name, info in infos.items():
            vi.add_info(name, info)

        return vi

    def add_info(self, info, values):
        """Add info.

        Parameters
        ----------
        info: str
            Info name.
        values: Dict[variable: str, Any]
            Values for some or all variables.
            Variables not specified will be filled with None.
        """
        if info not in self._infos:
            self._infos.append(info)
            self.__dict__.update({info: IterDict(
                dict(zip(self.var, [None]*self.n)))})

        self.__dict__[info].update(values)

    def add_infos_per_variable(self, var, infos):
        """Add infos for a single variable.

        Parameters
        ----------
        var: str
            Variable name.
        infos: Dict
            Infos name and values.
            {'info name': value}
        """
        for k, z in infos.items():
            self.add_info(k, {var: z})

    def add_variable(self, variable, **infos):
        """Add a variable with corresponding info.

        Parameters
        ----------
        variable: str
            Variable name.
        infos:
            Infos name and values.
            If an info present in the VI is not provided,
            it is filled with None for the new variable.
        """
        if not infos:
            infos = {}
        var_list = list(self.var) + [variable]
        self.var = tuple(var_list)

        self.n += 1
        self.idx.update({variable: self.n-1})
        self.add_infos_per_variable(variable, infos)

    def pop_variables(self, variables):
        """Remove variables from vi.

        Parameters
        ----------
        variables: List[str]
            Variables to remove.
        """
        if not isinstance(variables, list):
            variables = [variables]

        d = {k: self.__dict__[k] for k in self._infos}
        var_list = list(self.var)
        for v in variables:
            var_list.remove(v)
            self.n -= 1
            for z in d.values():
                z.pop(v)
        self.var = tuple(var_list)
        self.idx = IterDict({k: i for i, k in enumerate(var_list)})

    def add_kwargs(self, **kwargs):
        """Add keywords / attributes."""
        for k, z in kwargs.items():
            self.__setattr__(k, z)
            self._kwargs.append(k)
