"""Matcher object.

Handles matches in the pre-regex.
"""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


class Matcher():
    """Object associated with a matcher in the pre-regex.

    Holds (temporarily) the match for the current file.

    Parameters
    ----------
    m: re.match
        Match object of a matcher in the pre-regex.
        See FilegroupScan.scan_pregex().
    idx: int
        Index of the matcher in the full pre-regex

    Attributes
    ----------
    coord: str
        Coordinate name.
    idx: int
        Matcher index in the full pre-regex.
    elt: str
        Coordinate element.
    dummy: bool
        If the matcher is a dummy, ie not containing any
        information, or redondant information.
    ELT_RGX: Dict
        Regex str for each type of element.
    """

    ELT_RGX = {"idx": r"\d*",
               "x": r"\d\d\d\d\d\d\d\d",
               "Y": r"\d\d\d\d",
               "yy": r"\d\d",
               "M": r"[a-zA-Z]*",
               "mm": r"\d?\d",
               "dd": r"\d?\d",
               "doy": r"\d?\d?\d",
               "text": r"[a-zA-Z]*",
               "char": r"\S*"}

    def __init__(self, m, idx):
        coord = m.group(1)
        elt = m.group(2)
        custom = m.group('cus')
        rgx = m.group(4)[:-1]
        dummy = m.group(5)

        if elt == '':
            elt = 'idx'

        self.coord = coord
        self.elt = elt
        self.idx = idx
        self.dummy = dummy is not None

        if custom is not None:
            self.rgx = rgx
        else:
            self.rgx = self.ELT_RGX[elt]

    def __str__(self):
        s = '{0}:{1}, idx={2}'.format(self.coord, self.elt, self.idx)
        if self.dummy:
            s += ', dummy'
        return s
