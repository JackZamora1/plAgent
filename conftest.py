"""
Pytest configuration and shared fixtures for PLA Agent SDK tests.

This file is automatically loaded by pytest and provides:
- Shared fixtures for common test setup
- Custom markers for test categorization
- Performance metrics collection
- Test data factories
"""

import pytest
import os
import time
from pathlib import Path
from typing import Generator
import logging

# Configure logging for tests
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise during tests
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# ============================================================================
# Pytest Configuration Hooks
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Ensure output directories exist
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    test_output = output_dir / "test_results"
    test_output.mkdir(exist_ok=True)


def pytest_collection_modifyitems(config, items):
    """
    Modify test items after collection.

    Automatically marks tests based on naming conventions:
    - test_*_integration.py → integration
    - test_*_slow.py → slow
    - Tests with 'api' in name → api
    - Tests with 'database' in name → database
    """
    for item in items:
        # Auto-mark integration tests
        if "integration" in item.nodeid or "test_agent" in item.nodeid:
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.slow)

        # Auto-mark API tests
        if "anthropic" in item.nodeid or "test_agent" in item.nodeid:
            item.add_marker(pytest.mark.api)

        # Auto-mark database tests
        if "database" in item.nodeid:
            item.add_marker(pytest.mark.database)

        # Auto-mark batch tests
        if "batch" in item.nodeid:
            item.add_marker(pytest.mark.batch)
            item.add_marker(pytest.mark.slow)

        # Auto-mark unit tests (default)
        if not any(mark.name in ['integration', 'slow', 'batch']
                   for mark in item.iter_markers()):
            item.add_marker(pytest.mark.unit)


# ============================================================================
# Shared Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Get test data directory path."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def test_output_dir() -> Path:
    """Get test output directory path."""
    output_dir = Path(__file__).parent / "output" / "test_results"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture
def sample_source_text(test_data_dir) -> str:
    """Load sample obituary text for testing."""
    test_file = test_data_dir / "test_obituary.txt"
    if test_file.exists():
        return test_file.read_text(encoding='utf-8')
    else:
        # Fallback sample text
        return "林炳尧同志逝世。原南京军区副司令员林炳尧同志，于2023年1月15日在南京逝世，享年80岁。"


@pytest.fixture
def sample_officer_data() -> dict:
    """Sample officer biographical data for testing."""
    return {
        "name": "林炳尧",
        "pinyin_name": "Lín Bǐngyáo",
        "hometown": "福建省晋江市",
        "birth_date": "1943",
        "death_date": "2023-01-15",
        "enlistment_date": "1961",
        "party_membership_date": "1964",
        "promotions": [
            {"rank": "少将", "date": "1995"},
            {"rank": "中将", "date": "2002"}
        ],
        "notable_positions": ["原南京军区副司令员"],
        "source_url": "https://test.example.com/obituary.html",
        "confidence_score": 0.85
    }


@pytest.fixture
def api_key_available() -> bool:
    """Check if Anthropic API key is available."""
    return bool(os.getenv('ANTHROPIC_API_KEY'))


@pytest.fixture
def database_available() -> bool:
    """Check if database connection is available."""
    db_url = os.getenv('DATABASE_URL')
    db_user = os.getenv('DB_USER')
    return bool(db_url or db_user)


@pytest.fixture
def skip_if_no_api(api_key_available):
    """Skip test if API key is not available."""
    if not api_key_available:
        pytest.skip("ANTHROPIC_API_KEY not set - skipping API test")


@pytest.fixture
def skip_if_no_database(database_available):
    """Skip test if database is not available."""
    if not database_available:
        pytest.skip("Database credentials not set - skipping database test")


# ============================================================================
# Performance Metrics Fixtures
# ============================================================================

@pytest.fixture
def performance_tracker():
    """
    Track performance metrics for a test.

    Usage:
        def test_something(performance_tracker):
            performance_tracker.start()
            # ... test code ...
            performance_tracker.stop()
            assert performance_tracker.duration < 5.0
    """
    class PerformanceTracker:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.duration = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()
            if self.start_time:
                self.duration = self.end_time - self.start_time

        def __enter__(self):
            self.start()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.stop()

    return PerformanceTracker()


# ============================================================================
# Test Data Factories
# ============================================================================

@pytest.fixture
def make_officer_bio():
    """
    Factory for creating OfficerBio test instances.

    Usage:
        def test_something(make_officer_bio):
            officer = make_officer_bio(name="Test Officer")
    """
    from schema import OfficerBio

    def _make_officer_bio(**overrides):
        defaults = {
            "name": "测试军官",
            "pinyin_name": "Cèshì Jūnguān",
            "source_url": "https://test.example.com",
            "confidence_score": 0.9
        }
        defaults.update(overrides)
        return OfficerBio(**defaults)

    return _make_officer_bio


@pytest.fixture
def make_promotion():
    """
    Factory for creating Promotion test instances.

    Usage:
        def test_something(make_promotion):
            promotion = make_promotion(rank="少将", date="1995")
    """
    from schema import Promotion

    def _make_promotion(**overrides):
        defaults = {
            "rank": "少将",
            "date": "1995"
        }
        defaults.update(overrides)
        return Promotion(**defaults)

    return _make_promotion


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_test_files(test_output_dir):
    """
    Automatically cleanup test output files after each test.

    Set autouse=True to run for every test.
    """
    yield  # Test runs here

    # Cleanup test-specific files (optional)
    # This runs after each test completes
    pass


# ============================================================================
# CI/CD Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def is_ci() -> bool:
    """Check if running in CI/CD environment."""
    return bool(os.getenv('CI') or os.getenv('GITHUB_ACTIONS'))


@pytest.fixture(scope="session")
def test_timeout(is_ci) -> int:
    """Get test timeout in seconds (longer in CI)."""
    return 600 if is_ci else 300


@pytest.fixture(scope="session")
def extraction_result():
    """
    Session-scoped fixture providing extraction result from test obituary.

    This fixture:
    - Runs the full agent extraction once per test session
    - Caches the result for all tests that need it
    - Skips if ANTHROPIC_API_KEY is not available
    - Saves result to output/test_extraction.json

    Returns:
        AgentExtractionResult: Result from extracting test obituary

    Raises:
        pytest.skip: If API key is missing or test data not found
    """
    import os
    from pathlib import Path
    from agent import PLAgentSDK
    from tools.extraction_tools import extract_text_from_file
    import json

    # Check for API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        pytest.skip("ANTHROPIC_API_KEY required for agent integration tests")

    # Load test data
    test_file = Path(__file__).parent / "data" / "test_obituary.txt"
    if not test_file.exists():
        pytest.skip(f"Test data not found: {test_file}")

    # Load source text
    source_text = extract_text_from_file(str(test_file))

    # Run extraction with universal profile
    sdk = PLAgentSDK(require_db=False)
    result = sdk.extract_bio_agentic(
        source_text=source_text,
        source_url="https://www.news.cn/test/obituary.html",
        source_type="universal"
    )

    # Cache result to file for inspection
    output_file = Path(__file__).parent / "output" / "test_extraction.json"
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(
            result.to_dict(exclude_none=True),
            f,
            ensure_ascii=False,
            indent=2
        )

    return result


# ============================================================================
# Reporting Hooks
# ============================================================================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook to capture test results for custom reporting.

    This allows us to add custom metadata to test results.
    """
    outcome = yield
    report = outcome.get_result()

    # Add custom properties for HTML report
    if report.when == "call":
        # Add test category to report
        markers = [mark.name for mark in item.iter_markers()]
        report.user_properties.append(("markers", ", ".join(markers)))

        # Add duration
        report.user_properties.append(("duration", f"{report.duration:.3f}s"))


# ============================================================================
# Example Usage in Tests
# ============================================================================

"""
Example test file using these fixtures:

```python
import pytest
from schema import OfficerBio

def test_officer_bio_creation(make_officer_bio):
    # Use factory fixture
    officer = make_officer_bio(name="Test")
    assert officer.name == "Test"

def test_performance(performance_tracker):
    # Track performance
    with performance_tracker:
        # ... test code ...
        pass
    assert performance_tracker.duration < 1.0

@pytest.mark.api
@pytest.mark.slow
def test_agent_extraction(skip_if_no_api, sample_source_text):
    # This test requires API key and is marked as slow
    from agent import PLAgentSDK
    sdk = PLAgentSDK()
    result = sdk.extract_bio_agentic(sample_source_text, "test_url")
    assert result.success

def test_with_sample_data(sample_officer_data):
    # Use sample data fixture
    assert sample_officer_data['name'] == "林炳尧"
```
"""
