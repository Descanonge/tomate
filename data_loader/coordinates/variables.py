"""Variable coordinate."""


class Variables():
    """.

    Parameters
    ----------
    variables: str, List[str], optional
    """

    def __init__(self, *variables):
        self.var = [v for v in variables]
        self.name = 'var'

    def __str__(self):
        return str(self.var)

    def __repr__(self):
        return '\n'.join([super().__repr__(), str(self)])

    def idx(self, y):
        if isinstance(y, str):
            return self.var.index(y)
        return y

    def name(self, y):
        if isinstance(y, str):
            return y
        return self.var[y]

    def __getitem__(self, y):
        """.

        Parameters
        ----------
        y: int, str, List[int], List[str], slice
        """
        if isinstance(y, (int, str)):
            return self.var[self.idx(y)]

        if isinstance(y, slice):
            start = self.idx(y.start)
            stop = self.idx(y.stop)
            y = slice(start, stop, y.step)
            y = list(range(*y.indices(self.size)))

        out = [self.var[self.idx(i)] for i in y]
        return out

    def __iter__(self):
        return iter(self.var)

    @property
    def size(self):
        return len(self.var)

    def slice(self, variables=None, keyring=None):
        """.

        Parameters
        ----------
        variables: int, str, List[int], List[str]
        """
        if keyring is not None and 'var' in keyring:
            var = keyring['var']
        if variables is not None:
            var = variables
        if isinstance(var, str):
            var = [var]

        self.var = [self.var[self.idx(v)] for v in var]

    def copy(self):
        return Variables(self.var)

    def empty(self):
        self.var = None

    def has_data(self):
        return self.is_empty()

    def is_empty(self):
        return self.var is None
