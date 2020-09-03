"""Scanning functions but better."""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


from typing import (Any, Callable, Dict, List, Sequence, Tuple, TYPE_CHECKING,
                    Union)

from tomate.custom_types import File, KeyLikeStr
from tomate.keys.key import Key

if TYPE_CHECKING:
    from tomate.data_base import DataBase
    from tomate.filegroup.coord_scan import CoordScan
    from tomate.filegroup.filegroup_load import FilegroupLoad


class Scanner:
    """Scanning function with extras.

    Revolve around a function for scanning information from files on disk.

    :param kind: Type of function. Could be 'attr' for attribute, 'in' for
        in-file, or 'filename' for filename scanning.
    :param func: The scanning function.
    :param kwargs: Static keyword arguments.

    :attr kind: str: Type of scanning function.
    :attr func: Callable: The scanning function.
        It is still accessible with self.call()
    :attr kwargs: Dict[str, Any]: Static keyword arguments passed to the
        function when scanning.
    :attr to_scan: bool: If the function has to be called during scanning.

    Examples
    --------
    'attrs' type scanners for coordinates should take in a CoordScan and a file
    object, and return a dictionnary. 'gen' and 'var' type are scanners for
    filegroup attributes. They should take in a filegroup instance, a file
    object and for 'var' a list of variables to scan attributes for.

    See :func:`scan_coord_attributes_default`,
    :func:`scan_general_attributes_default`, and
    :func:`scan_variables_attributes_default` for more details.
    """
    def __init__(self, kind: str, func: Callable,
                 **kwargs: Dict[str, Any]):
        self.kind = kind
        self.func = func
        self.kwargs = kwargs
        self.to_scan = True

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def scan(self, *args, **kwargs):
        """Launch scan.

        Simple wrapper around self.func. Arguments are passed to the function,
        and supersede `self.kwargs`.
        """
        self.to_scan = False
        kwargs.update(self.kwargs)
        return self(*args, **kwargs)

    def copy(self) -> 'Scanner':
        """Return copy of self."""
        return self.__class__(self.kind, self.func, **self.kwargs.copy())

    @property
    def name(self) -> str:
        """Name of scanner."""
        try:
            name = self.func.__name__
        except AttributeError:
            name = ''
        return name

    def __bool__(self):
        """If is to scan."""
        return self.to_scan

    def __repr__(self):
        return f"{self.kind}: {self.name}"


class ScannerCS(Scanner):
    """Scanner for scanning coordinates.

    Will scan different 'elements' for a CoordScan object.

    :param kind: Type of function. Can be 'in' for in-file,
        or 'filename' for filename scanning.
    :param func: The scanning function. Should return the right number of
        elements, and take in the right arguments for the scanner type (see
        below).
    :param kwargs: Static keyword arguments.
    :param elts: Elements to scan.

    :attr kind: str: Type of scanning function.
    :attr func: Callable: The scanning function.
        It is still accessible with self.call()
    :attr kwargs: Dict[str, Any]: Static keyword arguments passed to the
        function when scanning.
    :attr to_scan: bool: If the function has to be called during scanning.
    :attr restrain: List[str]: If not empty, only these elements will be
        scanned.

    Examples
    --------
    'in' and 'filename' should take in a CoordScan, a file object (only for
    'in'), a list of values previously scanned, and return elements. Elements
    can be any object. The function can return elements for multiple values at a
    time. Elements should then be lists all of the same length, which will be
    concatenated to elements already scanned. To avoid concatenation use tuples.

    See :func:`scan_in_file_default`, :func:`scan_filename_default`,
    for more details.
    """
    def __init__(self, kind: List[str], func: Callable,
                 elts: List[str], **kwargs: Any):
        super().__init__(kind, func, **kwargs)
        self.elts = elts
        self.restrain = []

    @property
    def returns(self) -> List[str]:
        """Elements returned by the scanner."""
        if self.restrain:
            elts = [e for e in self.elts if e in self.restrain]
        else:
            elts = self.elts.copy()
        return elts

    def scan(self, *args, **kwargs) -> Dict[str, Any]:
        """Scan elements.

        Apply restrain if any.

        :param args: Arguments passed to function.
        :returns: Dictionnary of elements.
        """
        results = super().scan(*args, **kwargs)
        if not isinstance(results, tuple):
            results = tuple([results])
        if len(results) != len(self.elts):
            raise TypeError("Scan function '{}' did not return expected"
                            " number of results. Expected {}, returned {}"
                            .format(self.func.__name__, self.elts, len(results)))
        if self.restrain:
            results = self.restrain_results(results)
        return dict(zip(self.returns, results))

    def copy(self) -> 'ScannerCS':
        """Return copy of self."""
        return self.__class__(self.kind, self.func,
                              self.elts.copy(), **self.kwargs.copy())

    def __repr__(self):
        s = super().__repr__()
        if not self.restrain:
            elts = [str(e) for e in self.elts]
        else:
            elts = [f"({e})" if e in self.restrain
                    else str(e) for e in self.elts]
        return "{} ({})".format(s, ', '.join(elts))

    def restrain_results(self, results: Tuple) -> Tuple:
        """Apply restrain.

        :param results: Tuple of elements returned by the function.
        :returns: Return tuple of result with restrain applied
            (only elements of restrain are kept, and in order).
        """
        indices = [self.elts.index(r) for r in self.restrain]
        return tuple([results[i] for i in indices])


class PostLoadingFunc():
    """Function applied after loading data.

    Can be applied only when certain variables are loaded.

    :param: func: Function to call. Should take database as
        only positional argument.
    :param variable_key: Specify which variable should trigger the function. If
        None, any variable will trigger it. Variables must be specified by name.
    :param all_variables: If False (default), loading any variables in specified
        key will trigger function. If True, at least all variables in specified
        key must be loaded to trigger it.
    :param kwargs: Static keywords arguments passed to function.

    :attr func: Callable[DataBase]: The function to launch.
    :attr variable_key: Key: Variables that will trigger function.
    :attr all: bool: If any or all variables from variable_key
        will trigger function.
    :attr kwargs: Dict[str, Any]: Static keyword arguments.
    """
    def __init__(self, func: Callable[['DataBase'], None],
                 variable_key: KeyLikeStr = None,
                 all_variables: bool = False, **kwargs: Any):
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

    def copy(self) -> 'PostLoadingFunc':
        """Return copy of self."""
        return self.__class__(self.func, self.variable_key,
                              self.all, **self.kwargs.copy())

    @property
    def name(self) -> str:
        """Function name."""
        try:
            name = self.func.__name__
        except AttributeError:
            name = ''
        return name

    def is_to_launch(self, loaded: List[str]) -> bool:
        """If function should be triggered.

        :param loaded: List of variable being loaded.
        """
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
        """Launch function."""
        self(database, **self.kwargs)


def make_scanner(kind: str, elts: List[str]) -> ScannerCS:
    """Turn a function into a CoordScan Scanner.

    :param kind: Scanner kind.
    :param elts: Elements returned by function.
    """
    def decorator(func):
        scanner = ScannerCS(kind, func, elts)
        scanner.__doc__ = func.__doc__
        return scanner
    return decorator


def scan_filename_default(cs: 'CoordScan', values: Sequence,
                          **kwargs: Any) -> Union[Any, Tuple[Any],
                                                  Tuple[List[Any]]]:
    """Scan elements from a filename.

    Matches found by the regex are accessible from the matchers objects in the
    CoordScan object passed to the function (as cs).
    Accessible parts of the filename are defined by the filegroup pre-regex.

    :param cs: CoordScan object.
    :param values: Values scanned so far.
    :param kwargs: Static keywords arguments.

    :returns: Any number of elements. If there are multiple values, all elements
        must be lists of same length that will be concatenated to elements
        previously scanned. Use tuples to avoid concatenation.

    Notes
    -----
    See scan_library for various examples.
    :func:`get_date_from_matches<tomate.scan_library.get_date_from_matches>` for
    instance.
    """
    raise NotImplementedError()


def scan_in_file_default(cs: 'CoordScan', file: File, values: Sequence,
                         **kwargs: Any) -> Tuple[Union[Any, List[Any]]]:
    """Scan elements inside a file.

    :param cs: CoordScan object.
    :param file: Object to access file. The file is already opened by
        FilegroupScan.open_file().
    :param values: Values scanned so far.
    :param kwargs: Static keywords arguments.

    :returns: Any number of elements. If there are multiple values, all elements
        must be lists of same length that will be concatenated to elements
        previously scanned. Use tuples to avoid concatenation.

    Notes
    -----
    See scan_library for various examples.
    :func:`nc.scan_in_file<tomate.scan_library.nc.scan_in_file>` for instance.
    """
    raise NotImplementedError()


def scan_coord_attributes_default(cs: 'CoordScan',
                                  file: File) -> Dict[str, Any]:
    """Scan coordinate attributes.

    Attributes are set to the CoordScan by cs.set_attr().

    :param cs: CoordScan object.
    :param file: Object to access file. The file is already opened by
        FilegroupScan.open_file().

    :returns: Dictionnary of attributes {'name': value}. They will be added to
        the CoordScan object with cs.set_attr(name=value)
    """
    raise NotImplementedError()


def scan_general_attributes_default(fg: 'FilegroupLoad', file: File,
                                    **kwargs: Any) -> Dict[str, Any]:
    """Scan general attributes in file.

    :param file: Object to access file. The file is already opened by
        FilegroupSan.open_file().

    :returns: Dictionnary of attributes. {attribute name: attribute value}.
        Attributes are added to the VI as 'infos'.
    """
    raise NotImplementedError()


def scan_variables_attributes_default(
        fg: 'FilegroupLoad', file: File,
        **kwargs: Any) -> Dict[str, Dict[str, Any]]:
    """Scan variable specific attributes.

    :param file: Object to access file. The file is already opened by
        FilegroupScan.open_file().

    :returns: Attributes per variable. {variable name: {attribute name: value}}
        Attributes are added to the VI.
    """
    raise NotImplementedError()
