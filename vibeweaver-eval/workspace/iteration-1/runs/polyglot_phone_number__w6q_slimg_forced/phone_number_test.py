# Public interface:
# PhoneNumber.__init__(self, number)
# Convention: cleaned NANP number is exposed as PhoneNumber(number).number; invalid input raises ValueError.

import pytest

from phone_number import PhoneNumber


def test_cleans_number_without_punctuation():
    assert PhoneNumber("2234567890").number == "2234567890"


def test_cleans_number_with_hyphens():
    assert PhoneNumber("613-995-0253").number == "6139950253"


def test_cleans_number_with_dots():
    assert PhoneNumber("613.995.0253").number == "6139950253"


def test_cleans_number_with_spaces():
    assert PhoneNumber("613 995 0253").number == "6139950253"


def test_cleans_number_with_parentheses():
    assert PhoneNumber("(613) 995-0253").number == "6139950253"


def test_cleans_number_with_country_code():
    assert PhoneNumber("1 613 995 0253").number == "6139950253"


def test_cleans_number_with_plus_country_code():
    assert PhoneNumber("+1 (613)-995-0253").number == "6139950253"


def test_cleans_number_with_plus_country_code_and_dots():
    assert PhoneNumber("+1.613.995.0253").number == "6139950253"


def test_cleans_number_with_country_code_no_separator():
    assert PhoneNumber("16139950253").number == "6139950253"


def test_accepts_area_code_starting_with_2():
    assert PhoneNumber("2234567890").number == "2234567890"


def test_accepts_area_code_starting_with_9():
    assert PhoneNumber("9234567890").number == "9234567890"


def test_accepts_exchange_code_starting_with_2():
    assert PhoneNumber("2232567890").number == "2232567890"


def test_accepts_exchange_code_starting_with_9():
    assert PhoneNumber("2239567890").number == "2239567890"


def test_accepts_11_digit_number_starting_with_1():
    assert PhoneNumber("12234567890").number == "2234567890"


def test_invalid_empty_string():
    with pytest.raises(ValueError):
        PhoneNumber("")


def test_invalid_too_short():
    with pytest.raises(ValueError):
        PhoneNumber("223456789")


def test_invalid_too_long():
    with pytest.raises(ValueError):
        PhoneNumber("22345678901")


def test_invalid_11_digits_not_starting_with_1():
    with pytest.raises(ValueError):
        PhoneNumber("22234567890")


def test_invalid_12_digits():
    with pytest.raises(ValueError):
        PhoneNumber("321234567890")


def test_invalid_area_code_starts_with_0():
    with pytest.raises(ValueError):
        PhoneNumber("(023) 456-7890")


def test_invalid_area_code_starts_with_1():
    with pytest.raises(ValueError):
        PhoneNumber("(123) 456-7890")


def test_invalid_area_code_starts_with_1_with_country_code():
    with pytest.raises(ValueError):
        PhoneNumber("1 123 456 7890")


def test_invalid_exchange_code_starts_with_0():
    with pytest.raises(ValueError):
        PhoneNumber("(223) 056-7890")


def test_invalid_exchange_code_starts_with_1():
    with pytest.raises(ValueError):
        PhoneNumber("(223) 156-7890")


def test_invalid_exchange_code_starts_with_1_with_country_code():
    with pytest.raises(ValueError):
        PhoneNumber("1 (223) 156-7890")


def test_invalid_letters():
    with pytest.raises(ValueError):
        PhoneNumber("223-abc-7890")


def test_invalid_punctuation():
    with pytest.raises(ValueError):
        PhoneNumber("223-@:!-7890")


def test_invalid_country_code_2_with_plus():
    with pytest.raises(ValueError):
        PhoneNumber("+2 (223) 456-7890")


def test_invalid_country_code_2_without_plus():
    with pytest.raises(ValueError):
        PhoneNumber("2 223 456 7890")
