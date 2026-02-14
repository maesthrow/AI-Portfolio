"""Email address validation for CV sending."""
from __future__ import annotations

import re

# RFC 5322 simplified — catches 99%+ of real email addresses
_EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)

# Disposable / temporary email domains (extend as needed)
_BLOCKED_DOMAINS: frozenset[str] = frozenset({
    "tempmail.com",
    "throwaway.email",
    "guerrillamail.com",
    "guerrillamail.de",
    "mailinator.com",
    "10minutemail.com",
    "yopmail.com",
    "trashmail.com",
    "sharklasers.com",
    "guerrillamailblock.com",
    "grr.la",
    "dispostable.com",
    "temp-mail.org",
    "fakeinbox.com",
    "tempail.com",
    "mohmal.com",
})


def validate_email(email: str) -> tuple[bool, str | None]:
    """Validate email address format and domain.

    Returns:
        (is_valid, error_message) — error_message is None when valid.
    """
    email = email.strip().lower()

    if not email:
        return False, "Email-адрес не указан"

    if len(email) > 254:
        return False, "Email-адрес слишком длинный"

    if not _EMAIL_REGEX.match(email):
        return False, "Некорректный формат email"

    domain = email.rsplit("@", 1)[1]
    if domain in _BLOCKED_DOMAINS:
        return False, "Одноразовые email-адреса не поддерживаются"

    return True, None


def extract_email(text: str) -> str | None:
    """Extract first email address from free-form text.

    Returns lowercase email or None.
    """
    match = re.search(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        text,
    )
    return match.group(0).lower() if match else None
