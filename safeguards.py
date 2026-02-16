"""Shared safeguard checks for extraction inputs and outputs."""
from pathlib import Path
from typing import Iterable


SUSPICIOUS_URL_PATTERNS = ("example.com", "placeholder", "test.com", "localhost")
KNOWN_TEST_URL_PREFIXES = (
    "https://test/",
    "https://interactive/test",
    "https://local.test/",
)


def validate_real_source_url(source_url: str) -> tuple[bool, str]:
    """
    Validate source_url is not a placeholder URL.

    Returns:
        (is_valid, message)
    """
    lowered = (source_url or "").lower()
    for pattern in SUSPICIOUS_URL_PATTERNS:
        if pattern in lowered:
            return False, (
                f"source_url appears to be a placeholder: {source_url}. "
                "Please provide the actual source URL."
            )
    return True, "ok"


def validate_source_text_not_fixture(source_text: str, source_url: str, root: Path) -> None:
    """
    Reject extraction when source text exactly matches local test fixture content
    outside explicitly allowed test URL contexts.

    Raises:
        ValueError: if fixture leakage is detected.
    """
    test_file = root / "data" / "test_obituary.txt"
    if not test_file.exists():
        return

    test_content = test_file.read_text(encoding="utf-8").strip()
    is_known_test_context = source_url.startswith(KNOWN_TEST_URL_PREFIXES)

    if source_text.strip() == test_content and not is_known_test_context:
        raise ValueError(
            "SOURCE VALIDATION FAILED: received test_obituary.txt content "
            f"for non-test URL: {source_url}"
        )

