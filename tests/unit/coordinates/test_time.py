
import cftime
import pytest

from tomate.coordinates.time import Time

@pytest.fixture
def dates():
    dates = [
        [2000, 1, 10, 0],    # 0  /  15
        [2000, 1, 10, 6],    # 1  /  14
        [2000, 1, 10, 12],   # 2  /  13
        [2000, 1, 10, 18],   # 3  /  12

        [2000, 1, 11, 0],    # 4  /  11
        [2000, 1, 11, 6],    # 5  /  10
        [2000, 1, 11, 12],   # 6  /  9
        [2000, 1, 11, 18],   # 7  /  8

        [2000, 1, 13, 0],    # 8  /  7
        [2000, 1, 13, 6],    # 9  /  6
        [2000, 1, 13, 12],   # 10 /  5
        [2000, 1, 13, 18],   # 11 /  4

        [2000, 1, 15, 0],    # 12 /  3
        [2000, 1, 16, 0],    # 13 /  2
        [2000, 1, 17, 0],    # 14 /  1
        [2000, 1, 18, 12],   # 15 /  0
    ]
    return dates

@pytest.fixture
def coord(dates):
    units = 'hours since 2000-01-01 00:00:00'
    values = cftime.date2num([cftime.datetime(*d) for d in dates], units)
    return Time('time', values, units)


def test_index2date(coord, dates):
    dates = [cftime.DatetimeGregorian(*d) for d in dates]
    assert all(dates == coord.index2date())


def test_get_index(coord):
    f = coord.get_index
    assert f([2000, 1, 10, 5]) == 1
    assert f([2000, 1, 10, 5], 'below') == 0
    assert f([2000, 1, 13, 0]) == 8

    coord.update_values(coord[::-1])
    assert f([2000, 1, 10, 5]) == 14
    assert f([2000, 1, 10, 5], 'below') == 15
    assert f([2000, 1, 13, 0]) == 7


def test_get_index_by_day(coord):
    f = coord.get_index_by_day

    assert f([2000, 1, 10, 5]) == 1
    assert f([2000, 1, 10, 5], 'below') == 0
    assert f([2000, 1, 10, 7], 'above') == 2

    with pytest.raises(IndexError):
        f([2000, 1, 12])
    with pytest.raises(IndexError):
        f([2000, 1, 15, 1], 'above')
    with pytest.raises(IndexError):
        f([2000, 1, 18, 6], 'below')
    with pytest.raises(IndexError):
        f([2000, 1, 11, 20], 'above')

    coord.update_values(coord[::-1])

    assert f([2000, 1, 10, 5]) == 14
    assert f([2000, 1, 10, 5], 'below') == 15
    assert f([2000, 1, 10, 7], 'above') == 13

    with pytest.raises(IndexError):
        f([2000, 1, 12])
    with pytest.raises(IndexError):
        f([2000, 1, 15, 1], 'above')
    with pytest.raises(IndexError):
        f([2000, 1, 18, 6], 'below')
    with pytest.raises(IndexError):
        f([2000, 1, 11, 20], 'above')


def test_subset_by_day(coord):
    f = coord.subset_by_day

    assert f() == slice(0, 16, 1)
    assert f([2000, 1, 11, 0], [2000, 1, 13, 18]) == slice(4, 12, 1)
    assert f([2000, 1, 10], [2000, 1, 11]) == slice(0, 8, 1)
    assert f([2000, 1, 10], [2000, 1, 16]) == slice(0, 14, 1)
    assert f([2000, 1, 11], [2000, 1, 13], True) == slice(8, 8, 1)
    assert f([2000, 1, 10], [2000, 1, 16], True) == slice(4, 13, 1)
