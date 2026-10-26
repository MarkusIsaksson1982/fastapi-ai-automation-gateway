import pytest

from app.redaction import redact


@pytest.mark.parametrize(
    "text, email",
    [
        ("Contact a@b.se for details", "a@b.se"),
        ("Mail first.last+tag@example.co.uk today", "first.last+tag@example.co.uk"),
        ("a@b.se and c@d.org", "a@b.se"),
        ("a@b.se and c@d.org", "c@d.org"),
    ],
)
def test_redacts_email_addresses(text, email):
    result = redact(text)
    assert email not in result
    assert "[REDACTED_EMAIL]" in result


@pytest.mark.parametrize(
    "personnummer",
    [
        "19900101-1234",
        "900101-1234",
        "19900101+1234",
        "900101+1234",
        "199001011234",
        "9001011234",
    ],
)
def test_redacts_swedish_personnummer(personnummer):
    result = redact(f"Personnummer: {personnummer}")
    assert personnummer not in result
    assert "[REDACTED_PERSONNUMMER]" in result


@pytest.mark.parametrize(
    "phone",
    [
        "+46 70 123 45 67",
        "+46701234567",
        "070-123 45 67",
        "0701234567",
        "072 123 45 67",
        "073-123 45 67",
    ],
)
def test_redacts_swedish_phone_numbers(phone):
    result = redact(f"Ring {phone}")
    assert phone not in result
    assert "[REDACTED_PHONE]" in result


def test_redacts_all_pii_in_mixed_text():
    text = "Mail a@b.se, person 19900101-1234, ring 070-123 45 67"
    result = redact(text)
    assert "a@b.se" not in result
    assert "19900101-1234" not in result
    assert "070-123 45 67" not in result
    assert "[REDACTED_EMAIL]" in result
    assert "[REDACTED_PERSONNUMMER]" in result
    assert "[REDACTED_PHONE]" in result


@pytest.mark.parametrize(
    "text",
    [
        "This text has no personal information.",
        "Order 42 ships in three days.",
        "The meeting is at 10:30 on Monday.",
        "No PII here: just ordinary words and punctuation!",
    ],
)
def test_text_without_pii_is_unchanged(text):
    assert redact(text) == text
