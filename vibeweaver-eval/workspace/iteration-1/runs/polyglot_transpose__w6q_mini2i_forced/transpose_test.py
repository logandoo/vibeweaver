# Public interface:
# transpose(text) -> str

from transpose import transpose


def test_empty_string():
    assert transpose("") == ""


def test_single_space():
    assert transpose(" ") == "\x20"


def test_multiple_spaces():
    assert transpose("   ") == "\x20\n\x20\n\x20"


def test_single_character():
    assert transpose("A") == "A"


def test_single_row_multiple_characters():
    assert transpose("AB") == "A\nB"


def test_single_column_multiple_characters():
    assert transpose("A\nB") == "AB"


def test_square_matrix():
    assert transpose("ABC\nDEF") == "AD\nBE\nCF"


def test_rectangle_matrix():
    assert transpose("AB\nCD\nEF") == "ACE\nBDF"


def test_spec_example_first_line_longer():
    assert transpose("ABC\nDE") == "AD\nBE\nC"


def test_spec_example_second_line_longer():
    assert transpose("AB\nDEF") == "AD\nBE\n\x20F"


def test_single_line_with_internal_space():
    assert transpose("Single line.") == "S\ni\nn\ng\nl\ne\n\x20\nl\ni\nn\ne\n."


def test_trailing_space_on_top_row_is_preserved():
    assert transpose("A\x20\nB") == "AB\n\x20"


def test_trailing_space_on_bottom_row_is_preserved_with_padding():
    assert transpose("A\nB\x20") == "AB\n\x20\x20"


def test_multiple_trailing_spaces_on_top_row_are_preserved():
    assert transpose("A\x20\x20\nB") == "AB\n\x20\n\x20"


def test_empty_row_between_nonempty_rows():
    assert transpose("A\n\nB") == "A\x20B"


def test_leading_empty_row():
    assert transpose("\nA") == "\x20A"


def test_trailing_empty_row():
    assert transpose("A\n") == "A"


def test_triangle():
    assert transpose("A\nBB\nCCC") == "ABC\n\x20BC\n\x20\x20C"


def test_jagged_triangle():
    assert transpose("A\nBB\nCCC\nDDDD") == "ABCD\n\x20BCD\n\x20\x20CD\n\x20\x20\x20D"
