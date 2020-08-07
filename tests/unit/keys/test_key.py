
from tomate.keys.key import Key, list2slice, guess_slice_size


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


def test_multiplication():
    def test(k1, k2, k3, size=None):
        k1 = Key(k1)
        k1.parent_size = size
        assert k1 * Key(k2) == Key(k3)

    # None slices
    test(slice(None), 0, 0)
    test(slice(None), [0, 1, 2], [0, 1, 2])
    test(slice(10, 5, -1), slice(None), slice(10, 5, -1))

    test(10, 0, 10)
    test(10, [0], 10)
    test(10, slice(None), 10)

    test([10, 11], 0, 10)
    test([10, 11], 1, 11)
    test([10, 11], [0, 1], [10, 11])
    test([0, 1, 2, 3], slice(None), [0, 1, 2, 3])
    test([0, 1, 2, 3], slice(0, 2), [0, 1])
    test([0, 1, 2, 3], slice(3, None, -1), [3, 2, 1, 0])

    test(slice(0, 10), 3, 3, 10)
    test(slice(10, 20), [5, 3, 2], [15, 13, 12], 20)
    test(slice(10, 20), slice(0, 6, 2), slice(10, 15, 2), 20)
    test(slice(2, 18, 3), slice(1, 7, 2), slice(5, 18, 6), 20)


def test_addition():
    def test(k1, k2, k3, s1=None, s2=None):
        k1 = Key(k1)
        k2 = Key(k2)
        k1.parent_size = s1
        k2.parent_size = s2
        assert k1 + k2 == Key(k3)

    test(0, 0, [0, 0])
    test([0, 1, 3], 4, [0, 1, 3, 4])

    test(slice(10, 15), [15, 16], slice(10, 17, 1), 50)

    test(slice(0, 5), slice(20, 25), [0, 1, 2, 3, 4, 20, 21, 22, 23, 24], 50, 50)


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
