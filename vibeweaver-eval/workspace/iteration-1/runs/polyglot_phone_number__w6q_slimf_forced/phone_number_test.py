import pytest

from phone_number import PhoneNumber


def test_cleans_the_number():
    assert PhoneNumber("(223) 456-7890").number == "2234567890"


def test_cleans_numbers_with_dots():
    assert PhoneNumber("223.456.7890").number == "2234567890"


def test_cleans_numbers_with_multiple_spaces():
    assert PhoneNumber("223 456   7890   ").number == "2234567890"


def test_cleans_spec_examples():
    assert PhoneNumber("+1 (613)-995-0253").number == "6139950253"
    assert PhoneNumber("613-995-0253").number == "6139950253"
    assert PhoneNumber("1 613 995 0253").number == "6139950253"
    assert PhoneNumber("613.995.0253").number == "6139950253"


def test_invalid_when_9_digits():
    with pytest.raises(ValueError, match="^Invalid phone number$"):
        PhoneNumber("123456789")


def test_invalid_when_11_digits_does_not_start_with_a_1():
    with pytest.raises(ValueError, match="^Invalid phone number$"):
        PhoneNumber("22234567890")


def test_valid_when_11_digits_and_starting_with_1():
    assert PhoneNumber("12234567890").number == "2234567890"


def test_valid_when_11_digits_and_starting_with_1_even_with_punctuation():
    assert PhoneNumber("+1 (223) 456-7890").number == "2234567890"


def test_invalid_when_12_digits():
    with pytest.raises(ValueError, match="^Invalid phone number$"):
        PhoneNumber("123456789012")


def test_invalid_when_area_code_starts_with_0():
    with pytest.raises(ValueError, match="^Invalid phone number$"):
        PhoneNumber("0234567890")


def test_invalid_when_area_code_starts_with_1():
    with pytest.raises(ValueError, match="^Invalid phone number$"):
        PhoneNumber("1234567890")


def test_invalid_when_exchange_code_starts_with_0():
    with pytest.raises(ValueError, match="^Invalid phone number$"):
        PhoneNumber("2230567890")


def test_invalid_when_exchange_code_starts_with_1():
    with pytest.raises(ValueError, match="^Invalid phone number$"):
        PhoneNumber("2231567890")


def test_invalid_when_exchange_code_starts_with_0_and_area_code_starts_with_1():
    with pytest.raises(ValueError, match="^Invalid phone number$"):
        PhoneNumber("1230567890")


def test_invalid_when_exchange_code_starts_with_1_and_area_code_starts_with_0():
    with pytest.raises(ValueError, match="^Invalid phone number$"):
        PhoneNumber("0231567890")


def test_invalid_when_letters():
    with pytest.raises(ValueError, match="^Invalid phone number$"):
        PhoneNumber("223-abc-7890")


def test_invalid_when_punctuation():
    with pytest.raises(ValueError, match="^Invalid phone number$"):
        PhoneNumber("223-@:!-7890")


def test_invalid_when_empty():
    with pytest.raises(ValueError, match="^Invalid phone number$"):
        PhoneNumber("")


def test_invalid_when_no_digits():
    with pytest.raises(ValueError, match="^Invalid phone number$"):
        PhoneNumber("+()-.")


def test_area_code():
    assert PhoneNumber("2234567890").area_code == "223"


def test_area_code_with_country_code():
    assert PhoneNumber("+1 (613)-995-0253").area_code == "613"


def test_pretty_print():
    assert PhoneNumber("2234567890").pretty() == "(223) 456-7890"


def test_pretty_print_with_full_us_phone_number():
    assert PhoneNumber("12234567890").pretty() == "(223) 456-7890"


def test_pretty_print_spec_example():
    assert PhoneNumber("+1 (613)-995-0253").pretty() == "(613) 995-0253"
