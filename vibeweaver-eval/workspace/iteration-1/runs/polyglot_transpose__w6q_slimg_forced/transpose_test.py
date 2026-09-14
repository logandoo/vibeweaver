# Public interface:
# transpose(text: str) -> str

from transpose import transpose

def test_empty_string():
    assert transpose("") == ""

def test_single_character():
    assert transpose("A") == "A"

def test_single_row():
    assert transpose("A1B2") == "A\n1\nB\n2"

def test_single_column():
    assert transpose("A\n1\n2\n3") == "A123"

def test_two_by_two():
    assert transpose("AB\nCD") == "AC\nBD"

def test_rectangle():
    assert transpose("ABC\nDEF") == "AD\nBE\nCF"

def test_ragged_missing_bottom():
    assert transpose("ABC\nDE") == "AD\nBE\nC"

def test_ragged_missing_top():
    assert transpose("AB\nDEF") == "AD\nBE\n F"

def test_jagged():
    assert transpose("A1B2\nC3") == "AC\n13\nB\n2"

def test_jagged_with_spaces():
    assert transpose("A1B2\nC3 ") == "AC\n13\nB \n2"

def test_jagged_with_spaces_top():
    assert transpose("A \nBC") == "AB\n C"

def test_trailing_empty_row():
    assert transpose("A\n") == "A"

def test_leading_empty_row():
    assert transpose("\nA") == " A"

def test_multiple_empty_rows():
    assert transpose("\n\nA") == "  A"
