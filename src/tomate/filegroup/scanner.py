"""Scanning functions but better. """

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import List

from tomate.custom_types import KeyLikeStr
from tomate.keys.key import Key, is_none_slice


class Scanner:
    def __init__(self, kind, func, **kwargs):
        self.kind = kind
        self.func = func
        self.kwargs = kwargs
        self.to_scan = True

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def scan(self, *args, **kwargs):
        self.to_scan = False
        kwargs.update(self.kwargs)
        return self(*args, **kwargs)

    def copy(self):
        return self.__class__(self.kind, self.func, **self.kwargs.copy())

    @property
    def name(self) -> str:
        try:
            name = self.func.__name__
        except AttributeError:
            name = ''
        return name

    def __bool__(self):
        return self.to_scan

    def __repr__(self):
        s = ' - '.join([self.kind, self.name])
        return s


class ScannerCS(Scanner):
    def __init__(self, kind, func, elts, **kwargs):
        self.kind = kind
        self.func = func
        self.elts = elts
        self.kwargs = kwargs
        self.to_scan = True
        self.restrain = None

    @property
    def returns(self) -> List[str]:
        """Elements returned by the scanner."""
        if self.restrain is not None:
            elts = [e for e in self.elts if e in self.restrain]
        else:
            elts = self.elts.copy()
        return elts

    def scan(self, *args):
        results = super().scan(*args)
        if not isinstance(results, tuple):
            results = tuple([results])
        if len(results) != len(self.elts):
            raise TypeError("Scan function '{}' did not return expected"
                            " number of results. Expected {}, returned {}"
                            .format(self.func.__name__, self.elts, len(results)))
        if self.restrain is not None:
            results = self.restrain_results(results)
        return dict(zip(self.returns, results))

    def copy(self):
        return self.__class__(self.kind, self.func,
                              self.elts.copy(), **self.kwargs.copy())

    def __repr__(self):
        s = ' - '.join([self.kind, self.func.__name__, str(self.elts)])
        if self.restrain is not None:
            s += ' (restrained to {})'.format(self.restrain)
        return s

    def restrain_results(self, results):
        indices = [self.elts.index(r) for r in self.restrain]
        return tuple([results[i] for i in indices])


class PostLoadingFunc():
    def __init__(self, func, variable_key: KeyLikeStr = None,
                 all_variables=False, **kwargs):
        self.func = func
        self.kwargs = kwargs
        self.all = all_variables

        key = Key(variable_key)
        if not key.str and key.type != 'none':
            raise TypeError("Variables must be specified by name"
                            " or with None.")
        self.variable_key = key

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def copy(self):
        return self.__class__(self.func, self.variable_key,
                              self.all, **self.kwargs.copy())

    @property
    def name(self) -> str:
        try:
            name = self.func.__name__
        except AttributeError:
            name = ''
        return name

    def is_to_launch(self, loaded: List[str]) -> bool:
        if self.variable_key.type == 'none':
            return True
        loaded = set(loaded)
        selected = set(self.variable_key.as_list())
        if self.all:
            out = selected <= loaded
        else:
            out = len(selected & loaded) > 0
        return out

    def __repr__(self):
        s = ' - '.join([self.name])
        return s

    def launch(self, database):
        self(database, **self.kwargs)


def make_scanner(kind, elts):
    def decorator(func):
        return ScannerCS(kind, func, elts)
    return decorator
