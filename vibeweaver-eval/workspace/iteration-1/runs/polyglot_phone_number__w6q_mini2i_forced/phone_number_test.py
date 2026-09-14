# Public interface:
#   class PhoneNumber:
#       def __init__(self, number): ...
#
# Canonical convention for this exercise family:
#   PhoneNumber(number).number -> cleaned 10-digit NANP number string.
#   Invalid input raises ValueError.

import pytest

from phone_number import PhoneNumber


def test_cleans_plain_ten_digit_number():
    assert PhoneNumber("6139950253").number == "6139950253"


def test_cleans_number_with_parentheses_and_hyphens():
    assert PhoneNumber("(613)-995-0253").number == "6139950253"


def test_cleans_number_with_dots():
    assert PhoneNumber("613.995.0253").number == "6139950253"


def test_cleans_number_with_spaces():
    assert PhoneNumber("613 995 0253").number == "6139950253"


def test_cleans_number_with_multiple_spaces_and_trailing_space():
    assert PhoneNumber("613 995   0253   ").number == "6139950253"


def test_cleans_country_code_plus_one_with_punctuation():
    assert PhoneNumber("+1 (613)-995-0253").number == "6139950253"


def test_cleans_country_code_one_with_spaces():
    assert PhoneNumber("1 613 995 0253").number == "6139950253"


def test_cleans_country_code_one_without_separator():
    assert PhoneNumber("16139950253").number == "6139950253"


def test_cleans_plus_one_country_code_without_separator():
    assert PhoneNumber("+16139950253").number == "6139950253"


def test_cleans_eleven_digit_number_starting_with_one():
    assert PhoneNumber("12234567890").number == "2234567890"


def test_cleans_eleven_digit_number_starting_with_one_and_punctuation():
    assert PhoneNumber("+1 (223) 456-7890").number == "2234567890"


def test_valid_area_and_exchange_codes_can_start_with_two():
    assert PhoneNumber("2232567890").number == "2232567890"


def test_valid_area_and_exchange_codes_can_start_with_nine():
    assert PhoneNumber("9239567890").number == "9239567890"


def test_empty_string_is_invalid():
    with pytest.raises(ValueError):
        PhoneNumber("")


def test_whitespace_only_is_invalid():
    with pytest.raises(ValueError):
        PhoneNumber("   ")


def test_single_digit_is_invalid():
    with pytest.raises(ValueError):
        PhoneNumber("1")


def test_nine_digits_is_invalid():
    with pytest.raises(ValueError):
        PhoneNumber("123456789")


def test_twelve_digits_is_invalid():
    with pytest.raises(ValueError):
        PhoneNumber("321234567890")


def test_more_than_eleven_digits_is_invalid():
    with pytest.raises(ValueError):
        PhoneNumber("123234567890")


def test_eleven_digits_not_starting_with_one_is_invalid():
    with pytest.raises(ValueError):
        PhoneNumber("22234567890")


def test_eleven_digits_starting_with_zero_is_invalid():
    with pytest.raises(ValueError):
        PhoneNumber("02234567890")


def test_area_code_cannot_start_with_zero():
    with pytest.raises(ValueError):
        PhoneNumber("(023) 456-7890")


def test_area_code_cannot_start_with_one():
    with pytest.raises(ValueError):
        PhoneNumber("(123) 456-7890")


def test_exchange_code_cannot_start_with_zero():
    with pytest.raises(ValueError):
        PhoneNumber("(223) 056-7890")


def test_exchange_code_cannot_start_with_one():
    with pytest.raises(ValueError):
        PhoneNumber("(223) 156-7890")


def test_area_code_cannot_start_with_zero_after_country_code():
    with pytest.raises(ValueError):
        PhoneNumber("1 (023) 456-7890")


def test_area_code_cannot_start_with_one_after_country_code():
    with pytest.raises(ValueError):
        PhoneNumber("1 (123) 456-7890")


def test_exchange_code_cannot_start_with_zero_after_country_code():
    with pytest.raises(ValueError):
        PhoneNumber("1 (223) 056-7890")


def test_exchange_code_cannot_start_with_one_after_country_code():
    with pytest.raises(ValueError):
        PhoneNumber("1 (223) 156-7890")


def test_letters_are_invalid():
    with pytest.raises(ValueError):
        PhoneNumber("123-abc-7890")


def test_letters_are_invalid_even_when_ten_digits_remain():
    with pytest.raises(ValueError):
        PhoneNumber("223-456-abc7890")


def test_punctuation_other_than_allowed_is_invalid():
    with pytest.raises(ValueError):
        PhoneNumber("123-@:!-7890")


def test_punctuation_other_than_allowed_is_invalid_even_when_ten_digits_remain():
    with pytest.raises(ValueError):
        PhoneNumber("223-456-@7890")
