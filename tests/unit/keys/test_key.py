
from tomate.keys.key import Key, list2slice, reverse_slice_order


def test_reverse_slice():
    pass


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
    pass


def test_guess_tolist():
    pass


def test_multiplication():
    pass


def test_addition():
    pass
