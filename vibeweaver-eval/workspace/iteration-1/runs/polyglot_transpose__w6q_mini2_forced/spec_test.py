#!/usr/bin/env python3
"""Spec tests for transpose exercise."""
from transpose import transpose


def test_two_characters_single_column():
    """Transpose 'A\\nB' -> ['AB']"""
    result = transpose("A\nB")
    assert result == ["AB"]


def test_two_columns_single_row():
    """Transpose 'AB' -> ['A', 'B']"""
    result = transpose("AB")
    assert result == ["A", "B"]


def test_two_rows_two_columns():
    """
    ABC
    DEF
    -> AD, BE, CF
    """
    result = transpose("ABC\nDEF")
    assert result == ["AD", "BE", "CF"]


def test_unequal_rows_pad_left():
    """
    ABC
    DE
    -> AD, BE, C
    """
    result = transpose("ABC\nDE")
    assert result == ["AD", "BE", "C"]


def test_unequal_rows_pad_left_spaces():
    """
    AB
    DEF
    -> AD, BE, ' F'
    """
    result = transpose("AB\nDEF")
    assert result == ["AD", "BE", " F"]


def test_three_rows_three_columns():
    """
    ABC
    DEFG
    HIJ
    -> ADH, BEI, CFJ, ' G'
    """
    result = transpose("ABC\nDEFG\nHIJ")
    assert result == ["ADH", "BEI", "CFJ", " G"]


def test_single_line():
    """Transpose 'ABC' -> ['A', 'B', 'C']"""
    result = transpose("ABC")
    assert result == ["A", "B", "C"]


def test_empty_string():
    """Transpose '' -> ['']"""
    result = transpose("")
    assert result == [""]


def test_two_empty_lines():
    """Transpose '\\n' -> ['', '']"""
    result = transpose("\n")
    assert result == ["", ""]


def test_input_with_spaces():
    """
    space
    space
    -> ss, pp, aa, cc, ee
    """
    result = transpose("space\nspace")
    assert result == ["ss", "pp", "aa", "cc", "ee"]


def test_mixed_spaces_and_chars():
    """
    Vvv
    vVv
    vvv
    -> Vvv, vVv, vvv
    """
    result = transpose("Vvv\nvVv\nvvv")
    assert result == ["Vvv", "vVv", "vvv"]
