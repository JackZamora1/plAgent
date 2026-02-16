"""Offline smoke tests for core local behavior.

These tests avoid external API/network dependencies and validate:
- Public CLI command surface
- Safeguard allow/block behavior for fixture text contexts
- Schema/date validation path for save_officer_bio
"""
from pathlib import Path

import pytest

from cli import create_parser
from safeguards import validate_source_text_not_fixture
from tools.extraction_tools import execute_save_officer_bio

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_cli_public_commands_are_available():
    """CLI should expose only the supported top-level commands."""
    parser = create_parser()
    subparsers_action = next(
        action for action in parser._actions
        if getattr(action, "dest", None) == "command"
    )
    commands = set(subparsers_action.choices.keys())
    assert commands == {"extract", "batch", "validate", "interactive"}


def test_cli_removed_commands_are_rejected():
    """Removed commands should fail parser validation."""
    parser = create_parser()
    for removed in ("test", "replay", "stats", "batch-test", "batch-files"):
        with pytest.raises(SystemExit):
            parser.parse_args([removed])


def test_safeguard_allows_test_fixture_in_test_context():
    """Fixture text should be allowed when URL is in approved test context."""
    root = PROJECT_ROOT
    source_text = (root / "data" / "test_obituary.txt").read_text(encoding="utf-8")
    validate_source_text_not_fixture(source_text, "https://test/obituary.html", root)


def test_safeguard_blocks_test_fixture_in_non_test_context():
    """Fixture text should be rejected when URL is not in approved test context."""
    root = PROJECT_ROOT
    source_text = (root / "data" / "test_obituary.txt").read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        validate_source_text_not_fixture(
            source_text,
            "https://www.news.cn/test/obituary.html",
            root,
        )


def test_save_officer_bio_invalid_date_uses_date_validation_path():
    """Non-placeholder URL with bad date should fail due to date validation."""
    result = execute_save_officer_bio(
        {
            "name": "测试",
            "source_url": "https://www.news.cn/example/c.html",
            "birth_date": "95-01-01",
        }
    )
    assert not result.success
    assert result.error is not None
    assert "date" in result.error.lower() or "format" in result.error.lower()
