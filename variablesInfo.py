"""Stores metadata on the variables.

VariablesInfo: Stores various info in IterDict.
"""


from .iterDict import IterDict


class VariablesInfo():
    """Gives various info about all variables.

    Each info is stored in an IterDict.

    var gives key for an index
    idx gives the index for a key
    """

    def __init__(self, varList, infos, **kwargs):
        # Add the var and idx attributes
        self.var = tuple(varList)
        self.idx = IterDict({k: i for i, k in enumerate(varList)})
        self.n = len(varList)

        self._infos = []
        self.add_infos(infos)

        self.__dict__.update(kwargs)
        self._kwargs = list(kwargs.keys())

    def __iter__(self):
        """Enumerate over var."""
        return enumerate(self.var)

    def __getitem__(self, item):
        """Return VariableInfo slice."""

        keys = self.idx[item]
        if not isinstance(keys, list):
            keys = [keys]

        var = [self.var[i] for i in keys]

        d_new = {}
        for k in self._infos:
            z = self.__dict__[k]
            d_new.update({k: [list(z.values())[i] for i in keys]})

        kwargs = {k: self.__dict__[k] for k in self._kwargs}

        return VariablesInfo(var, d_new, **kwargs)

    def add_infos(self, infos):
        """Add infos.

        If keys already exist, previous info are
        discarded
        """
        for k, z in infos.items():
            mess = "'{:s}': Not as many values as variables".format(k)
            assert (len(z) == self.n), mess

            id = IterDict(dict(zip(self.var, z)))
            self.__dict__.update({k: id})
            if k not in self._infos:
                self._infos.append(k)

    def add_variable(self, var, **kwargs):
        """Add a variable with corresponding info.

        If info is not provided, it is filled with None
        """

        varList = list(self.var) + [var]
        self.var = tuple(varList)

        self.n += 1

        self.idx.update({var: self.n-1})
        d = self.__dict__
        keys = self._infos

        for k in keys:
            if k not in list(kwargs.keys()):
                kwargs.update({k: None})
        for k, z in kwargs.items():
            if k in d:
                d[k].update({var: z})
            else:   # The info is new
                L = [None]*self.n
                L[-1] = z
                d.update({k: IterDict(zip(self.var, L))})

    def pop_variables(self, variables):
        """Remove variables from vi."""

        if not isinstance(variables, list):
            variables = [variables]

        d = {k: self.__dict__[k] for k in self._infos}
        varList = list(self.var)
        for v in variables:
            varList.remove(v)
            self.n -= 1
            for z in d.values():
                z.pop(v)
        self.var = tuple(varList)
        self.idx = IterDict({k: i for i, k in enumerate(varList)})
