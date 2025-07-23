import re
import pytest

from app.core.security import verify_password, get_password_hash

PASSWORD = "SuperSecret123!"
OTHER = "NotTheRightOne"


def test_get_password_hash_returns_string_and_is_not_plaintext():
    hashed = get_password_hash(PASSWORD)
    # It should be a string, and must not equal the raw password
    assert isinstance(hashed, str)
    assert hashed != PASSWORD


def test_verify_password_with_correct_and_wrong():
    hashed = get_password_hash(PASSWORD)
    # Correct password should verify
    assert verify_password(PASSWORD, hashed) is True
    # Wrong password should not
    assert verify_password(OTHER, hashed) is False


def test_hash_is_random_per_call_but_both_verify():
    # Each call salts freshly, so hashes differ
    h1 = get_password_hash(PASSWORD)
    h2 = get_password_hash(PASSWORD)
    assert h1 != h2

    # But both still verify correctly
    assert verify_password(PASSWORD, h1)
    assert verify_password(PASSWORD, h2)


@pytest.mark.parametrize("scheme", ["bcrypt"])
def test_hash_scheme_prefix(scheme):
    # Ensure that bcrypt hashes actually use the bcrypt prefix
    # passlib may produce "$2b$" or "$2a$" etc, so we allow either
    hashed = get_password_hash(PASSWORD)
    assert re.match(r"^\$2[abxy]\$\d{2}\$", hashed), "Expected bcrypt‐style prefix"
