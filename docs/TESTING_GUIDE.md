# Testing Guide - PLA Agent SDK

Comprehensive guide to the test suite, including running tests, interpreting results, and contributing new tests.

## Table of Contents

- [Quick Start](#quick-start)
- [Test Suite Overview](#test-suite-overview)
- [Running Tests](#running-tests)
- [Test Reports](#test-reports)
- [Test Categories](#test-categories)
- [Writing Tests](#writing-tests)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Run All Tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Run comprehensive test suite
python run_all_tests.py
```

**Output:**
- `test_results.html` - Interactive HTML report with health score
- `test_results.json` - Machine-readable test data
- Terminal summary with pass/fail statistics

### Run Specific Test Categories

```bash
# Unit tests only (fast, no API required)
python run_all_tests.py --category unit

# Validation tests
python run_all_tests.py --category validation

# Integration tests (requires API key)
python run_all_tests.py --category integration

# Batch processing tests
python run_all_tests.py --category batch
```

### Fast Mode (Skip Slow Tests)

```bash
# Skip integration and batch tests
python run_all_tests.py --fast
```

---

## Test Suite Overview

### Test Structure

```
pla-agent-sdk/
├── run_all_tests.py          # Comprehensive test runner
├── pytest.ini                 # Pytest configuration
├── conftest.py                # Shared fixtures & plugins
│
├── test_schema.py             # Data model validation
├── test_config.py             # Configuration tests
├── test_tool_registry.py      # Tool system tests
├── test_validation_tools.py   # Validation tool tests
├── test_database_tools.py     # Database tool tests
├── test_agent.py              # Agent integration tests
├── test_anthropic_tools.py    # Anthropic API tests
├── test_workflow.py           # Workflow tests
└── test_batch_processor.py    # Batch processing tests
```

### Test Categories

| Category | Tests | Speed | Requirements |
|----------|-------|-------|--------------|
| **Unit** | Schema, Config, Tool Registry | Fast (~10s) | None |
| **Validation** | Validation Tools, Database Tools | Fast (~15s) | None |
| **Integration** | Agent, Anthropic Tools, Workflow | Slow (~60s) | API Key |
| **Batch** | Batch Processor | Slow (~30s) | API Key |

### System Health Score

The test runner calculates a health score (0-100) based on:

- **Pass Rate (60%)**: Percentage of tests passing
- **Critical Failures (30%)**: Penalty for errors (-5 points each)
- **Performance (10%)**: Bonus for fast execution

**Score Interpretation:**
- 90-100: EXCELLENT (production ready)
- 75-89: GOOD (minor issues)
- 60-74: FAIR (needs attention)
- 40-59: POOR (significant issues)
- 0-39: CRITICAL (major failures)

---

## Running Tests

### Basic Usage

```bash
# Run all tests with default settings
python run_all_tests.py

# Verbose output
python run_all_tests.py --verbose

# Fast mode (skip slow tests)
python run_all_tests.py --fast

# Specific category
python run_all_tests.py --category unit
```

### Using Pytest Directly

```bash
# Run all tests
pytest

# Run specific file
pytest test_schema.py

# Run specific test function
pytest test_schema.py::test_officer_bio_validation

# Run tests matching pattern
pytest -k "validation"

# Run with markers
pytest -m "unit"                    # Only unit tests
pytest -m "not slow"                # Skip slow tests
pytest -m "integration and not api" # Integration without API
```

### CI/CD Mode

```bash
# Minimal output for CI systems
python run_all_tests.py --ci

# Output (JSON):
{
  "success": true,
  "total_tests": 47,
  "passed": 44,
  "failed": 3,
  "skipped": 0,
  "duration": 125.5,
  "health_score": 87.3,
  "health_status": "GOOD"
}
```

---

## Test Reports

### HTML Report

**Location:** `test_results.html`

**Features:**
- ✅ Interactive test results with filtering
- ✅ System health score (0-100)
- ✅ Pass/fail statistics
- ✅ Detailed error messages
- ✅ Test duration metrics
- ✅ Beautiful gradient header

**Open in browser:**
```bash
# macOS
open test_results.html

# Linux
xdg-open test_results.html

# Windows
start test_results.html
```

### JSON Report

**Location:** `test_results.json`

**Structure:**
```json
{
  "created": "2026-02-12T23:30:00",
  "duration": 125.5,
  "summary": {
    "total": 47,
    "passed": 44,
    "failed": 3,
    "skipped": 0
  },
  "tests": [
    {
      "nodeid": "test_schema.py::test_officer_bio_creation",
      "outcome": "passed",
      "duration": 0.05,
      "markers": ["unit"]
    }
  ]
}
```

**Use cases:**
- Parse results in CI/CD pipelines
- Generate custom reports
- Track metrics over time
- Integrate with dashboards

---

## Test Categories

### Unit Tests (Fast)

**Files:**
- `test_schema.py` - Pydantic model validation
- `test_config.py` - Configuration loading
- `test_tool_registry.py` - Tool registration

**Run:**
```bash
python run_all_tests.py --category unit
```

**What they test:**
- Data model creation and validation
- Field validators (dates, names, URLs)
- Configuration parsing
- Tool registry operations

**No external dependencies** - Safe to run anytime

---

### Validation Tests (Fast)

**Files:**
- `test_validation_tools.py` - Date validation, information verification
- `test_database_tools.py` - Database tool definitions

**Run:**
```bash
python run_all_tests.py --category validation
```

**What they test:**
- Date chronology validation
- Information presence verification
- Tool input/output schemas
- Error handling

**No API required** - Tests tool logic only

---

### Integration Tests (Slow)

**Files:**
- `test_agent.py` - Full agent extraction workflow
- `test_anthropic_tools.py` - Anthropic API integration
- `test_workflow.py` - Multi-step workflows

**Run:**
```bash
# Requires ANTHROPIC_API_KEY in .env
python run_all_tests.py --category integration
```

**What they test:**
- End-to-end extraction from obituary text
- Claude API tool use
- Multi-turn conversations
- Error recovery and retries

**Requires API key** - Uses real Claude API calls

---

### Batch Processing Tests (Slow)

**Files:**
- `test_batch_processor.py` - Batch processing system

**Run:**
```bash
# Requires ANTHROPIC_API_KEY in .env
python run_all_tests.py --category batch
```

**What they test:**
- Processing multiple URLs
- Rate limiting
- Progress tracking
- Error handling across batches

**Requires API key** - May incur costs (~$0.10-0.20)

---

## Writing Tests

### Test File Template

```python
"""
Tests for [component name].

Test categories:
- Unit tests for [specific functionality]
- Edge cases for [specific scenarios]
- Error handling for [specific conditions]
"""

import pytest
from schema import OfficerBio, Promotion

# ============================================================================
# Unit Tests
# ============================================================================

@pytest.mark.unit
def test_basic_functionality():
    """Test basic functionality works as expected."""
    # Arrange
    data = {"name": "Test", "source_url": "https://test.com"}

    # Act
    result = OfficerBio(**data)

    # Assert
    assert result.name == "Test"


# ============================================================================
# Edge Cases
# ============================================================================

@pytest.mark.unit
def test_edge_case():
    """Test edge case handling."""
    with pytest.raises(ValueError):
        OfficerBio(name="", source_url="invalid")


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
def test_integration(skip_if_no_api):
    """Test integration with external service."""
    # This test requires API key
    pass
```

### Using Fixtures

```python
def test_with_sample_data(sample_officer_data):
    """Test using shared fixture."""
    assert sample_officer_data['name'] == "林炳尧"


def test_with_factory(make_officer_bio):
    """Test using factory fixture."""
    officer = make_officer_bio(name="Custom Name")
    assert officer.name == "Custom Name"


def test_with_performance_tracking(performance_tracker):
    """Test with performance measurement."""
    with performance_tracker:
        # ... test code ...
        pass

    assert performance_tracker.duration < 1.0
```

### Test Markers

```python
# Mark as unit test (default for non-slow tests)
@pytest.mark.unit
def test_unit():
    pass

# Mark as integration test
@pytest.mark.integration
def test_integration():
    pass

# Mark as slow (>5 seconds)
@pytest.mark.slow
def test_slow():
    pass

# Mark as requiring API
@pytest.mark.api
def test_api(skip_if_no_api):
    pass

# Mark as requiring database
@pytest.mark.database
def test_database(skip_if_no_database):
    pass

# Combine markers
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.api
def test_full_workflow(skip_if_no_api):
    pass
```

### Parametrized Tests

```python
@pytest.mark.parametrize("date_str,expected", [
    ("1995", True),
    ("1995-01-15", True),
    ("1995-13-01", False),  # Invalid month
    ("not-a-date", False),
])
def test_date_validation(date_str, expected):
    """Test date validation with multiple inputs."""
    # Test logic here
    pass
```

---

## CI/CD Integration

### GitHub Actions

The test suite is automatically run on GitHub Actions:

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`
- Manual workflow dispatch

**Jobs:**
1. **Unit & Validation Tests** - Run on every push (fast, no secrets)
2. **Integration Tests** - Run on `main` branch only (requires API key)

**Configuration:** `.github/workflows/tests.yml`

### Setting Up Secrets

**For GitHub Actions:**

1. Go to repository Settings → Secrets and variables → Actions
2. Add secret: `ANTHROPIC_API_KEY`
3. Tests will use this key automatically

### Local CI Mode

```bash
# Run in CI mode (minimal output)
python run_all_tests.py --ci

# Exits with:
# - 0 if all tests pass
# - 1 if any test fails
```

**Perfect for pre-commit hooks:**

```bash
# .git/hooks/pre-commit
#!/bin/bash
python run_all_tests.py --fast --ci
```

---

## Troubleshooting

### Tests Fail: "ANTHROPIC_API_KEY not set"

**Cause:** Integration tests require API key

**Solution:**
```bash
# Skip integration tests
python run_all_tests.py --category unit

# Or add API key to .env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
```

---

### Tests Fail: "Database credentials not set"

**Cause:** Database tests need PostgreSQL

**Solution:**
```bash
# These tests are optional - skip them
python run_all_tests.py --category unit

# Or configure database in .env
echo "DATABASE_URL=postgresql://..." >> .env
```

---

### Tests Taking Too Long

**Cause:** Integration tests are slow (~60s)

**Solution:**
```bash
# Use fast mode
python run_all_tests.py --fast

# Or run only unit tests
python run_all_tests.py --category unit
```

---

### Import Errors

**Cause:** Missing dependencies

**Solution:**
```bash
# Reinstall all dependencies
pip install -r requirements.txt

# Or install test dependencies specifically
pip install pytest pytest-html pytest-json-report
```

---

### HTML Report Not Generated

**Cause:** pytest-html not installed

**Solution:**
```bash
pip install pytest-html

# Then run tests again
python run_all_tests.py
```

---

### Tests Pass Locally But Fail in CI

**Possible causes:**
1. Different Python version
2. Missing environment variables
3. API rate limiting

**Solution:**
```bash
# Test with same Python version as CI
python3.11 run_all_tests.py --ci

# Check CI logs for specific error
# Update .github/workflows/tests.yml if needed
```

---

## Best Practices

### Before Committing Code

```bash
# Run fast tests
python run_all_tests.py --fast

# If all pass, run full suite
python run_all_tests.py
```

### Before Pull Requests

```bash
# Run comprehensive tests
python run_all_tests.py --verbose

# Check test_results.html for any warnings
open test_results.html

# Ensure health score > 75
```

### When Adding New Features

1. Write tests first (TDD)
2. Run relevant test category
3. Add markers appropriately
4. Update this guide if needed

### Performance Guidelines

- Unit tests: < 0.1s each
- Validation tests: < 0.5s each
- Integration tests: < 10s each
- Total suite: < 5 minutes

---

## Test Coverage

To check code coverage:

```bash
# Install coverage tool
pip install pytest-cov

# Run with coverage
pytest --cov=. --cov-report=html

# View report
open htmlcov/index.html
```

**Target coverage:** >80% for production code

---

## Contributing Tests

When adding new tests:

1. **Follow naming conventions**
   - File: `test_<component>.py`
   - Function: `test_<functionality>()`

2. **Add appropriate markers**
   - `@pytest.mark.unit` for fast tests
   - `@pytest.mark.integration` for API tests
   - `@pytest.mark.slow` for >5s tests

3. **Use fixtures** from `conftest.py`

4. **Document test purpose** in docstring

5. **Keep tests isolated** - No side effects

6. **Test one thing** per test function

---

## Further Reading

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [GitHub Actions](https://docs.github.com/en/actions)

---

**Questions?** Check existing tests for examples or open an issue.

**Last Updated:** February 2026
