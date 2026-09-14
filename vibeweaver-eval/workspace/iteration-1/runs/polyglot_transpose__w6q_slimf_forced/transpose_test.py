from transpose import transpose


def test_empty_string():
    assert transpose("") == ""


def test_single_character():
    assert transpose("A") == "A"


def test_two_characters_in_a_row():
    assert transpose("A1") == "A\n1"


def test_two_characters_in_a_column():
    assert transpose("A\n1") == "A1"


def test_simple_matrix():
    assert transpose("ABC\nDEF") == "AD\nBE\nCF"


def test_single_line():
    assert transpose("Single line.") == "S\ni\nn\ng\nl\ne\n \nl\ni\nn\ne\n."


def test_square_matrix():
    assert transpose("AB\nCD") == "AC\nBD"


def test_rectangle_matrix():
    assert transpose("AB\nCD\nEF") == "ACE\nBDF"


def test_first_line_longer_than_second_line():
    assert transpose("ABC\nDE") == "AD\nBE\nC"


def test_second_line_longer_than_first_line():
    assert transpose("AB\nDEF") == "AD\nBE\n F"


def test_multiple_ragged_lines_with_leading_spaces():
    assert transpose("A\nBC\nDEF") == "ABD\n CE\n  F"


def test_multiple_ragged_lines_with_trailing_spaces_omitted():
    assert transpose("ABC\nDE\nF") == "ADF\nBE\nC"


def test_bottom_row_spaces_are_preserved():
    assert transpose("AB\n  ") == "A \nB "


def test_bottom_row_spaces_preserved_in_some_columns():
    assert transpose("ABC\nD  ") == "AD\nB \nC "


def test_bottom_row_space_preserved_but_missing_column_omitted():
    assert transpose("ABC\nD ") == "AD\nB \nC"


def test_first_line_longer_with_preserved_space():
    assert transpose("The fourth line.\nThe fifth line.") == (
        "TT\n"
        "hh\n"
        "ee\n"
        "  \n"
        "ff\n"
        "oi\n"
        "uf\n"
        "rt\n"
        "th\n"
        "h \n"
        " l\n"
        "li\n"
        "in\n"
        "ne\n"
        "e.\n"
        "."
    )


def test_second_line_longer_with_preserved_space():
    assert transpose("The fifth line.\nThe fourth line.") == (
        "TT\n"
        "hh\n"
        "ee\n"
        "  \n"
        "ff\n"
        "io\n"
        "fu\n"
        "tr\n"
        "ht\n"
        " h\n"
        "l \n"
        "il\n"
        "ni\n"
        "en\n"
        ".e\n"
        " ."
    )
