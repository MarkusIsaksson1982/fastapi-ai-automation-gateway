import re

EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.\w{2,}\b")
PERSONNUMMER = re.compile(r"\b(?:\d{6}|\d{8})[-+]?\d{4}\b")
PHONE = re.compile(r"(?<!\d)(?:\+46\s?7\d|07\d)[\s-]?\d{2,3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)")


def redact(text: str) -> str:
    text = EMAIL.sub("[REDACTED_EMAIL]", text)
    text = PHONE.sub("[REDACTED_PHONE]", text)
    return PERSONNUMMER.sub("[REDACTED_PERSONNUMMER]", text)
