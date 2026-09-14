import list_ops


def test_append_empty_lists():
    assert list_ops.append([], []) == []


def test_append_list_to_empty_list():
    assert list_ops.append([], [1, 2, 3, 4]) == [1, 2, 3, 4]


def test_append_empty_list_to_list():
    assert list_ops.append([1, 2, 3, 4], []) == [1, 2, 3, 4]


def test_append_non_empty_lists():
    assert list_ops.append([1, 2], [3, 4, 5]) == [1, 2, 3, 4, 5]


def test_concat_empty_list():
    assert list_ops.concat([]) == []


def test_concat_list_of_empty_lists():
    assert list_ops.concat([[], []]) == []


def test_concat_non_empty_lists():
    assert list_ops.concat([[1, 2], [3], [], [4, 5, 6]]) == [1, 2, 3, 4, 5, 6]


def test_filter_empty_list():
    assert list_ops.filter(lambda x: x % 2 == 1, []) == []


def test_filter_non_empty_list():
    assert list_ops.filter(lambda x: x % 2 == 1, [1, 2, 3, 4, 5]) == [1, 3, 5]


def test_filter_all_items():
    assert list_ops.filter(lambda x: True, [1, 2, 3]) == [1, 2, 3]


def test_filter_no_items():
    assert list_ops.filter(lambda x: False, [1, 2, 3]) == []


def test_length_empty_list():
    assert list_ops.length([]) == 0


def test_length_non_empty_list():
    assert list_ops.length([1, 2, 3, 4]) == 4


def test_length_single_item():
    assert list_ops.length([1]) == 1


def test_map_empty_list():
    assert list_ops.map(lambda x: x * 2, []) == []


def test_map_non_empty_list():
    assert list_ops.map(lambda x: x * 2, [1, 2, 3]) == [2, 4, 6]


def test_map_square():
    assert list_ops.map(lambda x: x * x, [1, 2, 3, 4]) == [1, 4, 9, 16]


def test_foldl_empty_list():
    assert list_ops.foldl(lambda acc, x: acc + x, [], 5) == 5


def test_foldl_non_empty_list():
    assert list_ops.foldl(lambda acc, x: acc + x, [1, 2, 3, 4], 5) == 15


def test_foldl_difference_order():
    assert list_ops.foldl(lambda acc, x: acc - x, [1, 2, 3], 0) == -6


def test_foldl_accumulate_list():
    assert list_ops.foldl(lambda acc, x: acc + [x], [1, 2, 3], []) == [1, 2, 3]


def test_foldr_empty_list():
    assert list_ops.foldr(lambda x, acc: acc + x, [], 5) == 5


def test_foldr_non_empty_list():
    assert list_ops.foldr(lambda x, acc: x + acc, [1, 2, 3, 4], 5) == 15


def test_foldr_difference_order():
    assert list_ops.foldr(lambda x, acc: x - acc, [1, 2, 3], 0) == 2


def test_foldr_accumulate_list():
    assert list_ops.foldr(lambda x, acc: acc + [x], [1, 2, 3], []) == [3, 2, 1]


def test_reverse_empty_list():
    assert list_ops.reverse([]) == []


def test_reverse_single_item():
    assert list_ops.reverse([1]) == [1]


def test_reverse_non_empty_list():
    assert list_ops.reverse([1, 2, 3, 4]) == [4, 3, 2, 1]


def test_reverse_strings():
    assert list_ops.reverse(["a", "b", "c"]) == ["c", "b", "a"]
