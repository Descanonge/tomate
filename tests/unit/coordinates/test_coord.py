
import pytest

import numpy as np

from tomate import Coord


@pytest.fixture
def values():
    a = np.arange(10)
    return a


@pytest.fixture
def coord(values):
    c = Coord('coord_test', values)
    return c


def test_descending(values, coord):
    coord.update_values(values[::-1])
    assert coord.is_descending()


def test_regular(coord):
    assert coord.is_regular()

    a = coord[:].copy()
    a[5] += 1e-4
    coord.update_values(a)

    assert not coord.is_regular()


def test_get_step(coord):

    def test(c):
        step = c.get_step()
        assert (step < 0) == c.is_descending()
        assert abs(step) - 1. < 1e-9

    test(coord)
    coord.update_values(coord[::-1])
    test(coord)


def test_get_index(coord):
    locs = ['below', 'above', 'closest']

    def test(c):
        step = 1 / (c.size-1)
        indices = [0, 1, 3, 8, 9]

        for i in indices:
            a = c[i]
            for loc in locs:
                assert c.get_index(a, loc) == i

            if not c.is_descending():
                b = a + step / 10.
                assert c.get_index(b, 'below') == i
                assert c.get_index(b, 'closest') == i
                assert c.get_index(b, 'above') == min(i+1, c.size-1)

                b = a - step / 10.
                assert c.get_index(b, 'below') == max(i-1, 0)
                assert c.get_index(b, 'closest') == i
                assert c.get_index(b, 'above') == i

            else:
                b = a + step / 10.
                assert c.get_index(b, 'below') == i
                assert c.get_index(b, 'closest') == i
                assert c.get_index(b, 'above') == max(i-1, 0)

                b = a - step / 10.
                assert c.get_index(b, 'below') == min(i+1, c.size-1)
                assert c.get_index(b, 'closest') == i
                assert c.get_index(b, 'above') == i

    test(coord)
    coord.update_values(coord[::-1])
    test(coord)


def test_get_index_exact(coord):

    def test(c):
        # Out of bounds values
        assert c.get_index_exact(15) is None
        assert c.get_index_exact(-1) is None

        # Value not in list
        a = (c[5] + c[6])/2.
        assert c.get_index_exact(a) is None

        # Random values in list
        indices = [0, 1, 4, 6, 8, 9]
        for i in indices:
            a = c[i]
            assert c.get_index_exact(a) == i

    test(coord)
    coord.update_values(coord[::-1])
    test(coord)


def test_subset(coord):
    c = coord

    # Extrema
    assert c.subset(exclude=False) == slice(0, c.size, 1)
    assert c.subset(exclude=True) == slice(1, c.size-1, 1)

    # OOB
    assert c.subset(-1, 15, exclude=False) == slice(0, c.size, 1)
    assert c.subset(-1, 15, exclude=True) == slice(0, c.size, 1)

    # Various
    assert c.subset(2, 4) == slice(2, 5, 1)
    assert c.subset(6, 9) == slice(6, 10, 1)
    assert c.subset(6, 9, exclude=True) == slice(7, 9, 1)

    assert c.subset(3.4, 7.4) == slice(3, 9, 1)
    assert c.subset(3.4, 7.4, exclude=True) == slice(4, 8, 1)


def test_subset_desc(coord):
    c = coord
    c.update_values(coord[::-1])

    # Extrema
    assert c.subset(exclude=False) == slice(0, c.size, 1)
    assert c.subset(exclude=True) == slice(1, c.size-1, 1)

    # OOB
    assert c.subset(-1, 15, exclude=False) == slice(0, c.size, 1)
    assert c.subset(-1, 15, exclude=True) == slice(0, c.size, 1)

    # Various
    assert c.subset(2, 4) == slice(5, 8, 1)
    assert c.subset(6, 9) == slice(0, 4, 1)
    assert c.subset(6, 9, exclude=True) == slice(1, 3, 1)

    assert c.subset(3.4, 7.4) == slice(1, 7, 1)
    assert c.subset(3.4, 7.4, exclude=True) == slice(2, 6, 1)
