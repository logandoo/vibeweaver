#!/usr/bin/env python3
"""Tests for list_ops — one per requirement, expected values from the spec."""
from list_ops import append, concat, filter, length, map, foldl, foldr, reverse


def test_append():
    assert append([1, 2], [3, 4]) == [1, 2, 3, 4]


def test_append_empty_first():
    assert append([], [1]) == [1]


def test_append_empty_second():
    assert append([1], []) == [1]


def test_append_both_empty():
    assert append([], []) == []


def test_concat():
    assert concat([[1, 2], [3], [], [4, 5]]) == [1, 2, 3, 4, 5]


def test_concat_empty():
    assert concat([]) == []


def test_concat_single():
    assert concat([[1, 2, 3]]) == [1, 2, 3]


def test_concat_all_empty():
    assert concat([[], []]) == []


def test_filter_even():
    assert filter(lambda x: x % 2 == 0, [1, 2, 3, 4, 5]) == [2, 4]


def test_filter_none():
    assert filter(lambda x: x > 10, [1, 2, 3]) == []


def test_filter_all():
    assert filter(lambda x: x >= 0, [-1, 0, 1]) == [0, 1]


def test_filter_empty():
    assert filter(lambda x: True, []) == []


def test_length():
    assert length([1, 2, 3]) == 3


def test_length_empty():
    assert length([]) == 0


def test_length_single():
    assert length([42]) == 1


def test_map_double():
    assert map(lambda x: x * 2, [1, 2, 3]) == [2, 4, 6]


def test_map_identity():
    assert map(lambda x: x, [1, 2, 3]) == [1, 2, 3]


def test_map_empty():
    assert map(lambda x: x, []) == []


def test_foldl():
    assert foldl(lambda acc, x: acc + x, [1, 2, 3, 4], 0) == 10


def test_foldl_subtract():
    assert foldl(lambda acc, x: acc - x, [1, 2, 3, 4], 10) == 0


def test_foldl_empty():
    assert foldl(lambda acc, x: acc + x, [], 5) == 5


def test_foldr():
    assert foldr(lambda acc, x: acc + x, [1, 2, 3, 4], 0) == 10


def test_foldr_divide():
    assert foldr(lambda acc, x: acc / x, [1, 2, 3, 4], 24) == 1


def test_foldr_empty():
    assert foldr(lambda acc, x: acc + x, [], 5) == 5


def test_reverse():
    assert reverse([1, 2, 3]) == [3, 2, 1]


def test_reverse_single():
    assert reverse([42]) == [42]


def test_reverse_empty():
    assert reverse([]) == []


def test_reverse_palindrome():
    assert reverse([1, 2, 3, 2, 1]) == [1, 2, 3, 2, 1]
