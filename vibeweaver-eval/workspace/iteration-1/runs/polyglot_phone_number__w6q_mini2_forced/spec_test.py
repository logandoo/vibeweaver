from phone_number import PhoneNumber


def test_cleans_number():
    p = PhoneNumber("6139950253")
    assert p.number == "6139950253"


def test_cleans_number_with_dots():
    p = PhoneNumber("613.995.0253")
    assert p.number == "6139950253"


def test_cleans_number_with_dashes():
    p = PhoneNumber("613-995-0253")
    assert p.number == "6139950253"


def test_cleans_number_with_parens():
    p = PhoneNumber("(613)9950253")
    assert p.number == "6139950253"


def test_cleans_number_with_country_code():
    p = PhoneNumber("1 613 995 0253")
    assert p.number == "6139950253"


def test_cleans_number_with_country_code_and_parens():
    p = PhoneNumber("+1 (613)-995-0253")
    assert p.number == "6139950253"


def test_invalid_when_area_code_starts_with_0():
    p = PhoneNumber("0139950253")
    assert p.number == "invalid"


def test_invalid_when_area_code_starts_with_1():
    p = PhoneNumber("1139950253")
    assert p.number == "invalid"


def test_invalid_when_exchange_code_starts_with_0():
    p = PhoneNumber("6130950253")
    assert p.number == "invalid"


def test_invalid_when_exchange_code_starts_with_1():
    p = PhoneNumber("6131950253")
    assert p.number == "invalid"


def test_invalid_when_9_digits():
    p = PhoneNumber("123456789")
    assert p.number == "invalid"


def test_invalid_when_11_digits_without_country_code():
    p = PhoneNumber("21234567890")
    assert p.number == "invalid"


def test_invalid_with_letters():
    p = PhoneNumber("123-abc-7890")
    assert p.number == "invalid"


def test_invalid_with_punctuations():
    p = PhoneNumber("123-@:!-7890")
    assert p.number == "invalid"


def test_invalid_with_country_code_and_bad_area_code():
    p = PhoneNumber("1 (013) 995-0253")
    assert p.number == "invalid"


def test_invalid_with_country_code_and_bad_exchange_code():
    p = PhoneNumber("1 (210) 195-0253")
    assert p.number == "invalid"
