"""Matcher object.

Handles matches in the pre-regex.
"""

# This file is part of the 'tomate' project
# (http://github.com/Descanonge/tomate) and subject
# to the MIT License as defined in the file 'LICENSE',
# at the root of this project. © 2020 Clément HAËCK


import re


class Matcher():
    """Object associated with a matcher in the pre-regex.

    Holds (temporarily) the match for the current file.

    :param m: Match object of a matcher in the pre-regex.
        See FilegroupScan.scan_pregex().
    :param idx: Index of the matcher in the full pre-regex

    :attr coord: str: Coordinate name.
    :attr idx: int: Matcher index in the full pre-regex.
    :attr elt: str: Coordinate element.
    :attr dummy: bool: If the matcher is a dummy, ie not containing any
        information, or redundant information.
    """

    ELT_RGX = {"idx": r"\d+",
               "Y": r"\d\d\d\d",
               "m": r"\d\d",
               "d": r"\d\d",
               "j": r"\d\d\d",
               "H": r"\d\d",
               "M": r"\d\d",
               "S": r"\d\d",
               "x": r"%Y%m%d",
               "X": r"%H%M%S",
               "B": r"[a-zA-Z]*",
               "text": r"[a-zA-Z]*",
               "char": r"\S*"}
    """Regex str for each type of element."""

    def __init__(self, m: re.match, idx: int):
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

        self.rgx = self.process_regex(self.rgx)

    @classmethod
    def process_regex(cls, rgx):
        """Replace elements.

        % followed by a single letter is replaced by the corresponding
        regex from `ELT_RGX`.
        %% is replaced by a single percentage character.
        """
        def replace(match):
            group = match.group(1)
            if group == '%':
                return '%'
            if group in cls.ELT_RGX:
                replacement = cls.ELT_RGX[group]
                if '%' in replacement:
                    return cls.process_regex(replacement)
                return replacement
            raise KeyError("Unknown replacement '{}'.".format(match.group(0)))
        rgx_new = re.sub("%([a-zA-Z%])", replace, rgx)
        return rgx_new

    def __repr__(self):
        s = '{0}:{1}, idx={2}'.format(self.coord, self.elt, self.idx)
        if self.dummy:
            s += ', dummy'
        return s
