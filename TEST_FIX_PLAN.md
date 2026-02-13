# Test Fix Plan - PLA Agent SDK

## Test Results Summary

**Run Date:** February 12, 2026, 23:28
**Total Tests:** 53
**Passed:** 50 ✅
**Failed:** 0
**Errors:** 3 ❌
**Success Rate:** 94.3%

---

## Failed Tests Analysis

### Error Summary

All 3 errors are in `test_agent.py` and have the same root cause:

```
FIXTURE NOT FOUND ERROR
E   fixture 'result' not found
```

**Failing Tests:**
1. `test_agent.py::test_control_variables` - Line 86
2. `test_agent.py::test_date_validation` - Line 143
3. `test_agent.py::test_database_integration` - Line 272

---

## Root Cause Analysis

### Problem

The `test_agent.py` file was designed as a **standalone test script** with sequential test execution:

```python
def main():
    # Test 1: Run extraction
    result = test_single_extraction()

    # Test 2: Check control variables (uses result from Test 1)
    passed, errors = test_control_variables(result)

    # Test 3: Validate dates (uses result from Test 1)
    passed, errors = test_date_validation(result)

    # Test 4: Check database (uses result from Test 1)
    passed, errors = test_database_integration(result)
```

**How it works standalone:**
1. `main()` calls `test_single_extraction()` → returns `AgentExtractionResult`
2. `main()` passes that result to subsequent tests
3. Tests run sequentially with shared state

**Why pytest fails:**
1. Pytest discovers all functions starting with `test_*`
2. Pytest tries to run each test **independently**
3. Tests expect `result` parameter → pytest treats it as a fixture
4. No fixture named `result` exists → ERROR

---

## Solution Approach

We need to make `test_agent.py` **compatible with both pytest and standalone execution**.

### Option 1: Create Pytest Fixtures (RECOMMENDED)

Add a session-scoped fixture that runs extraction once and shares the result:

```python
import pytest

@pytest.fixture(scope="session")
def extraction_result():
    """
    Run extraction once and share result across tests.

    This fixture:
    - Runs the full agent extraction
    - Caches the result for all tests
    - Skips if API key is missing
    """
    # Check for API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        pytest.skip("ANTHROPIC_API_KEY not set")

    # Run extraction
    test_file = Path(__file__).parent / "data" / "test_obituary.txt"
    source_text = extract_text_from_file(str(test_file))

    sdk = PLAgentSDK(require_db=False)
    result = sdk.extract_bio_agentic(
        source_text=source_text,
        source_url="https://www.news.cn/test/obituary.html",
        source_type="universal"
    )

    return result

# Then rename the parameter in tests:
def test_control_variables(extraction_result: AgentExtractionResult):
    # Use extraction_result instead of result
    ...
```

**Pros:**
- ✅ Works with pytest
- ✅ Extraction runs only once (cached)
- ✅ Tests can still depend on extraction
- ✅ Proper pytest integration

**Cons:**
- ⚠️ Requires API key for tests
- ⚠️ Tests become interdependent

---

### Option 2: Rename Functions (ALTERNATIVE)

Rename test functions to not match pytest's discovery pattern:

```python
# Old (pytest discovers these):
def test_control_variables(result):
    ...

# New (pytest ignores these):
def verify_control_variables(result):
    ...

# Keep the actual pytest test separate:
@pytest.mark.integration
def test_full_agent_workflow():
    """Pytest test that runs the full workflow."""
    result = test_single_extraction()
    verify_control_variables(result)
    verify_date_validation(result)
    verify_database_integration(result)
```

**Pros:**
- ✅ Minimal changes
- ✅ Standalone script still works
- ✅ Clear separation of concerns

**Cons:**
- ⚠️ Less granular test reporting
- ⚠️ Not idiomatic pytest

---

### Option 3: Skip for Pytest (QUICK FIX)

Mark tests to skip when run by pytest:

```python
import sys

# Only run these when called from main()
if 'pytest' not in sys.modules:
    def test_control_variables(result):
        ...
else:
    # Create pytest-compatible versions
    @pytest.mark.skip(reason="Requires standalone execution")
    def test_control_variables():
        pass
```

**Pros:**
- ✅ Quick fix
- ✅ Standalone script works
- ✅ No test failures in pytest

**Cons:**
- ⚠️ Tests skipped in pytest (reduced coverage)
- ⚠️ Messy code

---

## Recommended Solution: Option 1 + Refactoring

### Implementation Plan

#### Phase 1: Add Pytest Fixtures (Immediate Fix)

**File:** `conftest.py`

```python
import pytest
import os
from pathlib import Path
from agent import PLAgentSDK
from tools.extraction_tools import extract_text_from_file
from schema import AgentExtractionResult

@pytest.fixture(scope="session")
def extraction_result():
    """
    Session-scoped fixture providing extraction result.

    Runs once per test session and caches the result.
    Skips if API key is not available.
    """
    # Check for API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        pytest.skip("ANTHROPIC_API_KEY required for agent tests")

    # Load test data
    test_file = Path(__file__).parent / "data" / "test_obituary.txt"
    if not test_file.exists():
        pytest.skip(f"Test data not found: {test_file}")

    source_text = extract_text_from_file(str(test_file))

    # Run extraction
    sdk = PLAgentSDK(require_db=False)
    result = sdk.extract_bio_agentic(
        source_text=source_text,
        source_url="https://www.news.cn/test/obituary.html",
        source_type="universal"
    )

    # Cache result for inspection
    output_file = Path(__file__).parent / "output" / "test_extraction.json"
    output_file.parent.mkdir(exist_ok=True)

    import json
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(
            result.to_dict(exclude_none=True),
            f,
            ensure_ascii=False,
            indent=2
        )

    return result
```

**File:** `test_agent.py` (changes needed)

```python
# Line 85: Rename parameter
def test_control_variables(extraction_result: AgentExtractionResult) -> Tuple[bool, List[str]]:
    """Test that control variables are null."""
    # Change all references from 'result' to 'extraction_result'
    if not extraction_result.success or not extraction_result.officer_bio:
        ...

# Line 143: Rename parameter
def test_date_validation(extraction_result: AgentExtractionResult) -> Tuple[bool, List[str]]:
    """Test date validation logic."""
    if not extraction_result.success or not extraction_result.officer_bio:
        ...

# Line 272: Rename parameter
def test_database_integration(extraction_result: AgentExtractionResult) -> Tuple[bool, List[str]]:
    """Test database integration."""
    if not extraction_result.success or not extraction_result.officer_bio:
        ...
```

---

#### Phase 2: Add Pytest Markers (Better Organization)

```python
import pytest

@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.api
def test_control_variables(extraction_result):
    """Test control variables (integration test)."""
    ...

@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.api
def test_date_validation(extraction_result):
    """Test date validation (integration test)."""
    ...

@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.database
def test_database_integration(extraction_result):
    """Test database integration (integration test)."""
    ...
```

This allows selective test execution:
```bash
# Run only unit tests (skip these)
pytest -m "unit"

# Run integration tests
pytest -m "integration"

# Skip slow tests
pytest -m "not slow"
```

---

#### Phase 3: Improve Test Independence (Best Practice)

Make each test work independently by creating helper functions:

```python
def _get_test_result():
    """Helper to get test extraction result."""
    test_file = Path(__file__).parent / "data" / "test_obituary.txt"
    source_text = extract_text_from_file(str(test_file))
    sdk = PLAgentSDK(require_db=False)
    return sdk.extract_bio_agentic(source_text, "test_url", source_type="universal")

@pytest.mark.integration
def test_control_variables_independent():
    """Test control variables (independent version)."""
    result = _get_test_result()

    if not result.success:
        pytest.fail("Extraction failed")

    officer = result.officer_bio

    # Test control variables
    assert officer.wife_name is None, "wife_name should be null"
    assert officer.retirement_date is None, "retirement_date should be null"

    # Verify these were actually verified by agent
    verify_calls = [tc for tc in result.tool_calls
                   if tc.tool_name == "verify_information_present"]
    assert len(verify_calls) > 0, "Should verify optional fields"
```

**Pros:**
- ✅ Each test is truly independent
- ✅ Tests can run in any order
- ✅ Better for parallel execution
- ✅ More maintainable

---

## Action Items

### Immediate (Fix Test Failures)

- [ ] **Add `extraction_result` fixture to `conftest.py`**
  - Session-scoped fixture
  - Runs extraction once
  - Caches result
  - Skips if no API key

- [ ] **Update `test_agent.py` parameter names**
  - Line 85: `result` → `extraction_result`
  - Line 143: `result` → `extraction_result`
  - Line 272: `result` → `extraction_result`
  - Update all references in function bodies

- [ ] **Add pytest markers**
  - Mark as `@pytest.mark.integration`
  - Mark as `@pytest.mark.slow`
  - Mark as `@pytest.mark.api`

- [ ] **Test the fix**
  - Run: `pytest test_agent.py -v`
  - Should show 0 errors
  - All tests pass or skip gracefully

---

### Short-term (Improve Test Quality)

- [ ] **Keep standalone execution working**
  - Ensure `python test_agent.py` still works
  - main() should still call functions directly
  - No breaking changes to existing workflow

- [ ] **Add test documentation**
  - Document that agent tests require API key
  - Add skip message explaining why
  - Update TESTING_GUIDE.md

- [ ] **Verify in CI/CD**
  - Run tests in GitHub Actions
  - Ensure secrets are configured
  - Verify tests pass in CI environment

---

### Long-term (Best Practices)

- [ ] **Refactor for independence**
  - Create helper function for extraction
  - Make each test self-contained
  - Allow parallel execution

- [ ] **Add more granular tests**
  - Test individual tool calls
  - Test error handling
  - Test edge cases

- [ ] **Mock API calls for unit tests**
  - Create mock responses
  - Test logic without API calls
  - Faster test execution

---

## Testing the Fix

### Step 1: Add the fixture

```bash
# Edit conftest.py and add extraction_result fixture
nano conftest.py
```

### Step 2: Update test_agent.py

```bash
# Update parameter names
sed -i '' 's/def test_control_variables(result:/def test_control_variables(extraction_result:/g' test_agent.py
sed -i '' 's/def test_date_validation(result:/def test_date_validation(extraction_result:/g' test_agent.py
sed -i '' 's/def test_database_integration(result:/def test_database_integration(extraction_result:/g' test_agent.py

# Update references in function bodies
# (Do this manually to ensure correctness)
```

### Step 3: Run tests

```bash
# Run all tests
python run_all_tests.py

# Or run just agent tests
pytest test_agent.py -v

# Expected output:
# test_agent.py::test_control_variables PASSED
# test_agent.py::test_date_validation PASSED
# test_agent.py::test_database_integration PASSED
```

### Step 4: Verify standalone still works

```bash
# Run as standalone script
python test_agent.py

# Should work with main() orchestration
```

---

## Success Criteria

✅ **All pytest runs pass**
- 0 errors
- 0 failures
- Tests pass or skip appropriately

✅ **Standalone execution works**
- `python test_agent.py` runs successfully
- main() function works as before

✅ **CI/CD passes**
- GitHub Actions runs tests
- Integration tests run on main branch

✅ **Documentation updated**
- TESTING_GUIDE.md reflects changes
- conftest.py has clear docstrings

---

## Risk Assessment

**Low Risk:**
- Changes are isolated to test infrastructure
- Production code unaffected
- Backward compatible with standalone execution

**Medium Risk:**
- Requires API key for integration tests
- Tests now run extraction every time (costs tokens)

**Mitigation:**
- Use session-scoped fixture (runs once)
- Skip tests if API key missing
- Document API requirements clearly

---

## Alternative: Quick Fix (If Time Constrained)

If you need a quick fix without refactoring:

```python
# At top of test_agent.py
import pytest

# Wrap the problematic tests
@pytest.fixture
def result():
    """Dummy fixture to prevent errors."""
    pytest.skip("Use standalone execution: python test_agent.py")

# Tests will skip with clear message
```

This makes pytest skip the tests instead of erroring, buying time for proper fix.

---

## Estimated Effort

| Task | Time | Priority |
|------|------|----------|
| Add extraction_result fixture | 15 min | HIGH |
| Update test_agent.py parameters | 10 min | HIGH |
| Add pytest markers | 5 min | MEDIUM |
| Test locally | 10 min | HIGH |
| Update documentation | 15 min | MEDIUM |
| Verify in CI/CD | 10 min | MEDIUM |
| **TOTAL** | **65 min** | - |

---

## Next Steps

1. **Review this plan** - Confirm approach
2. **Implement fixture** - Add to conftest.py
3. **Update tests** - Rename parameters
4. **Run tests** - Verify fix works
5. **Update docs** - Document changes
6. **Commit** - Push to repository

---

**Ready to proceed?** Let me know if you want me to implement this fix now, or if you'd like to discuss the approach first.
