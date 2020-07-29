
from tomate.keys.key import (Key, list2slice, reverse_slice_order,
                             guess_slice_size)


def test_reverse_slice():
    f = reverse_slice_order

    # None slices
    assert f(slice(None)) == slice(None, None, -1)
    assert f(slice(None, None, -1)) == slice(None, None, 1)
    assert f(slice(None, None, 2)) == slice(None, None, -2)
    assert f(slice(None, None, -3)) == slice(None, None, 3)

    # Start with None
    assert f(slice(None, 10)) == slice(9, None, -1)
    assert f(slice(None, 10, 2)) == slice(9, None, -2)
    assert f(slice(None, -1)) == slice(-2, None, -1)

    assert f(slice(None, 4, -1)) == slice(5, None, 1)
    assert f(slice(None, 7, -2)) == slice(8, None, 2)

    # End with None
    assert f(slice(0, None, 1)) == slice(None, None, -1)
    assert f(slice(0, None, 3)) == slice(None, None, -3)

    assert f(slice(6, None, -1)) == slice(None, 7, 1)
    assert f(slice(6, None, -3)) == slice(None, 7, 3)

    # Random
    assert f(slice(3, 5, 1)) == slice(4, 2, -1)
    assert f(slice(4, 9, 2)) == slice(8, 3, -2)
    assert f(slice(0, 13, 3)) == slice(12, None, -3)
    assert f(slice(0, 14, 3)) == slice(13, None, -3)

    assert f(slice(4, 2, -1)) == slice(3, 5, 1)
    assert f(slice(8, 3, -2)) == slice(4, 9, 2)
    assert f(slice(12, None, -3)) == slice(None, 13, 3)
    assert f(slice(13, None, -3)) == slice(None, 14, 3)


def test_list2slice():
    f = list2slice

    # Stays list
    assert f([]) == []
    assert f([0]) == [0]
    assert f([0, 2, -4, -3]) == [0, 2, -4, -3]

    # Basic list
    assert f([0, 1]) == slice(0, 2, 1)
    assert f([0, 1, 2, 3, 4]) == slice(0, 5, 1)
    assert f([3, 4, 5, 6]) == slice(3, 7, 1)

    # Larger step
    assert f([0, 2, 4, 6, 8]) == slice(0, 9, 2)
    assert f([1, 3, 5]) == slice(1, 6, 2)
    assert f([2, 5, 8, 11]) == slice(2, 12, 3)

    # Negative index
    assert f([-5, -4, -3]) == slice(-5, -2, 1)
    assert f([-3, -2, -1]) == slice(-3, None, 1)

    # Negative step
    assert f([7, 5, 3]) == slice(7, 2, -2)
    assert f([3, 2, 1]) == slice(3, 0, -1)
    assert f([3, 2, 1, 0]) == slice(3, None, -1)
    assert f([-1, -3, -5]) == slice(-1, -6, -2)


def test_guess_size():
    f = guess_slice_size

    # Fail
    assert f(slice(None)) is None
    assert f(slice(0, None)) is None
    assert f(slice(None, -5)) is None

    assert f(slice(None, None, -1)) is None
    assert f(slice(-2, None, -1)) is None
    assert f(slice(None, 4, -1)) is None

    # Normal slice
    assert f(slice(0, 10)) == 10
    assert f(slice(4, 9)) == 5
    assert f(slice(None, 5)) == 5
    assert f(slice(-5, None)) == 5

    assert f(slice(10, None, -1)) == 11
    assert f(slice(8, 3, -1)) == 5
    assert f(slice(None, -5, -1)) == 4
    assert f(slice(5, None, -1)) == 6

    # Edge case
    assert f(slice(None, 0)) == 0
    assert f(slice(5, 0)) == 0
    assert f(slice(0, 2)) == 2
    assert f(slice(0, 1)) == 1
    assert f(slice(-1, None)) == 1
    assert f(slice(0, None, -1)) == 1
    assert f(slice(None, -2, -1)) == 1
    assert f(slice(None, -1, -1)) == 0

    # Large steps
    assert f(slice(0, 9, 2)) == 5
    assert f(slice(0, 8, 2)) == 4
    assert f(slice(None, 5, 2)) == 3
    assert f(slice(-5, None, 2)) == 3
    assert f(slice(1, 10, 3)) == 3
    assert f(slice(1, 11, 3)) == 4
    assert f(slice(1, 12, 3)) == 4

    assert f(slice(10, 4, -2)) == 3
    assert f(slice(9, None, -2)) == 5
    assert f(slice(8, None, -2)) == 5
    assert f(slice(None, -5, -2)) == 2
    assert f(slice(5, None, -2)) == 3
    assert f(slice(10, 4, -3)) == 2
    assert f(slice(10, 3, -3)) == 3
    assert f(slice(10, 2, -3)) == 3


def test_guess_tolist():
    pass


def test_multiplication():
    pass


def test_addition():
    pass
