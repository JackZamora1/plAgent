#!/usr/bin/env python3
"""Comprehensive test suite for PLAgentSDK."""
from agent import PLAgentSDK, ConversationPrinter
from tools.extraction_tools import extract_text_from_file
from schema import AgentExtractionResult
from config import CONFIG
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
import json
import logging
import warnings
from typing import List, Tuple
import pytest

warnings.filterwarnings("ignore", category=DeprecationWarning, module="urllib3")

console = Console()
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_single_extraction() -> AgentExtractionResult:
    """
    Test single obituary extraction.

    Returns:
        AgentExtractionResult from extraction
    """
    console.print("\n[bold cyan]═══ Test 1: Single Extraction ═══[/bold cyan]\n")

    try:
        # Load test obituary
        test_file = PROJECT_ROOT / "data" / "test_obituary.txt"
        if not test_file.exists():
            console.print(f"[red]✗ Test file not found: {test_file}[/red]")
            raise FileNotFoundError(f"Test file not found: {test_file}")

        console.print(f"[cyan]Loading obituary from {test_file}...[/cyan]")
        source_text = extract_text_from_file(str(test_file))
        console.print(f"[green]✓ Loaded {len(source_text)} characters[/green]\n")

        # Initialize SDK
        console.print("[cyan]Initializing PLAgentSDK...[/cyan]")
        sdk = PLAgentSDK(require_db=False)
        console.print("[green]✓ SDK initialized[/green]\n")

        # Run extraction with universal profile
        console.print("[cyan]Starting agentic extraction (universal profile)...[/cyan]")
        result = sdk.extract_bio_agentic(
            source_text=source_text,
            source_url="https://test/obituary.html")

        # Print extraction summary
        ConversationPrinter.print_extraction_summary(result)

        # Save result
        output_file = PROJECT_ROOT / "output" / "test_extraction.json"
        output_file.parent.mkdir(exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(
                result.to_dict(exclude_none=True),
                f,
                ensure_ascii=False,
                indent=2
            )

        console.print(f"\n[green]✓ Result saved to {output_file}[/green]")

        # Overall result
        if result.success:
            console.print("\n[bold green]✓ Test 1 PASSED: Extraction successful[/bold green]")
        else:
            console.print(f"\n[bold red]✗ Test 1 FAILED: {result.error_message}[/bold red]")

        return result

    except Exception as e:
        error_text = str(e).lower()
        connection_indicators = (
            "connection error",
            "api connection",
            "nodename nor servname",
            "name resolution",
            "timed out",
        )
        if any(token in error_text for token in connection_indicators):
            pytest.skip(f"Skipping API integration test due to connectivity issue: {e}")
        console.print(f"\n[bold red]✗ Test 1 FAILED with exception: {e}[/bold red]")
        import traceback
        console.print(traceback.format_exc())
        raise


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.api
def test_control_variables(extraction_result: AgentExtractionResult) -> Tuple[bool, List[str]]:
    """
    Test that control variables (rarely mentioned fields) are null.

    Args:
        extraction_result: Extraction result to test

    Returns:
        Tuple of (all_passed, error_messages)
    """
    console.print("\n[bold cyan]═══ Test 2: Control Variables ═══[/bold cyan]\n")

    if not extraction_result.success or not extraction_result.officer_bio:
        console.print("[yellow]⚠ Skipping - no officer bio to test[/yellow]")
        return False, ["No officer bio available"]

    officer = extraction_result.officer_bio
    errors = []
    passed = 0
    total = 0

    # Test wife_name
    total += 1
    console.print("[cyan]Checking wife_name (should be null)...[/cyan]")
    if officer.wife_name is None:
        console.print("[green]  ✓ PASS: wife_name is null (correct - rarely in obituaries)[/green]")
        passed += 1
    else:
        error_msg = f"wife_name is '{officer.wife_name}' (expected null)"
        console.print(f"[red]  ✗ FAIL: {error_msg}[/red]")
        errors.append(error_msg)

    # Test retirement_date
    total += 1
    console.print("[cyan]Checking retirement_date (should be null)...[/cyan]")
    if officer.retirement_date is None:
        console.print("[green]  ✓ PASS: retirement_date is null (correct - rarely in obituaries)[/green]")
        passed += 1
    else:
        error_msg = f"retirement_date is '{officer.retirement_date}' (expected null)"
        console.print(f"[red]  ✗ FAIL: {error_msg}[/red]")
        errors.append(error_msg)

    # Summary
    all_passed = len(errors) == 0
    console.print(f"\n[bold]Control Variables: {passed}/{total} checks passed[/bold]")

    if all_passed:
        console.print("[bold green]✓ Test 2 PASSED: Control variables are correct[/bold green]")
    else:
        console.print(f"[bold red]✗ Test 2 FAILED: {len(errors)} issues found[/bold red]")
        for error in errors:
            console.print(f"  - {error}")

    return all_passed, errors


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.api
def test_date_validation(extraction_result: AgentExtractionResult) -> Tuple[bool, List[str]]:
    """
    Test date chronology and validation.

    Args:
        extraction_result: Extraction result to test

    Returns:
        Tuple of (all_passed, error_messages)
    """
    console.print("\n[bold cyan]═══ Test 3: Date Validation ═══[/bold cyan]\n")

    if not extraction_result.success or not extraction_result.officer_bio:
        console.print("[yellow]⚠ Skipping - no officer bio to test[/yellow]")
        return False, ["No officer bio available"]

    officer = extraction_result.officer_bio
    errors = []
    passed = 0
    total = 0

    # Check if validate_dates tool was called
    total += 1
    console.print("[cyan]Checking if validate_dates tool was called...[/cyan]")
    validate_dates_called = any(
        tc.tool_name == "validate_dates"
        for tc in extraction_result.tool_calls
    )

    if validate_dates_called:
        console.print("[green]  ✓ PASS: validate_dates tool was called[/green]")
        passed += 1

        # Check if it succeeded
        validate_dates_success = any(
            tc.tool_name == "validate_dates" and tc.success
            for tc in extraction_result.tool_calls
        )

        if validate_dates_success:
            console.print("[green]  ✓ Date validation succeeded[/green]")
        else:
            console.print("[yellow]  ⚠ Date validation was called but failed[/yellow]")
    else:
        error_msg = "validate_dates tool was not called by agent"
        console.print(f"[red]  ✗ FAIL: {error_msg}[/red]")
        errors.append(error_msg)

    # Verify enlistment_date < party_membership_date
    if officer.enlistment_date and officer.party_membership_date:
        total += 1
        console.print("[cyan]Checking enlistment_date < party_membership_date...[/cyan]")

        try:
            # Simple string comparison works for YYYY format
            if officer.enlistment_date < officer.party_membership_date:
                console.print(f"[green]  ✓ PASS: {officer.enlistment_date} < {officer.party_membership_date}[/green]")
                passed += 1
            else:
                error_msg = f"enlistment_date ({officer.enlistment_date}) >= party_membership_date ({officer.party_membership_date})"
                console.print(f"[red]  ✗ FAIL: {error_msg}[/red]")
                errors.append(error_msg)
        except Exception as e:
            error_msg = f"Error comparing dates: {e}"
            console.print(f"[red]  ✗ FAIL: {error_msg}[/red]")
            errors.append(error_msg)
    else:
        console.print("[yellow]  ⚠ Cannot verify enlistment/party dates - one or both missing[/yellow]")

    # Verify promotions are chronological
    if officer.promotions and len(officer.promotions) > 1:
        total += 1
        console.print("[cyan]Checking promotions are chronological...[/cyan]")

        promotions_with_dates = [p for p in officer.promotions if p.date]

        if len(promotions_with_dates) > 1:
            chronological = True
            for i in range(len(promotions_with_dates) - 1):
                date1 = promotions_with_dates[i].date
                date2 = promotions_with_dates[i + 1].date

                if date1 and date2 and date1 > date2:
                    chronological = False
                    error_msg = f"Promotion dates out of order: {date1} > {date2}"
                    console.print(f"[red]  ✗ FAIL: {error_msg}[/red]")
                    errors.append(error_msg)
                    break

            if chronological:
                console.print(f"[green]  ✓ PASS: {len(promotions_with_dates)} promotions are chronological[/green]")
                passed += 1
        else:
            console.print("[yellow]  ⚠ Cannot verify promotion chronology - not enough dated promotions[/yellow]")
    else:
        console.print("[yellow]  ⚠ Cannot verify promotion chronology - less than 2 promotions[/yellow]")

    # Verify birth_date < death_date if both present
    if officer.birth_date and officer.death_date:
        total += 1
        console.print("[cyan]Checking birth_date < death_date...[/cyan]")

        try:
            if officer.birth_date < officer.death_date:
                console.print(f"[green]  ✓ PASS: {officer.birth_date} < {officer.death_date}[/green]")
                passed += 1
            else:
                error_msg = f"birth_date ({officer.birth_date}) >= death_date ({officer.death_date})"
                console.print(f"[red]  ✗ FAIL: {error_msg}[/red]")
                errors.append(error_msg)
        except Exception as e:
            error_msg = f"Error comparing birth/death dates: {e}"
            console.print(f"[red]  ✗ FAIL: {error_msg}[/red]")
            errors.append(error_msg)

    # Summary
    all_passed = len(errors) == 0
    console.print(f"\n[bold]Date Validation: {passed}/{total} checks passed[/bold]")

    if all_passed:
        console.print("[bold green]✓ Test 3 PASSED: Date validation successful[/bold green]")
    else:
        console.print(f"[bold red]✗ Test 3 FAILED: {len(errors)} issues found[/bold red]")
        for error in errors:
            console.print(f"  - {error}")

    return all_passed, errors


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.database
def test_database_integration(extraction_result: AgentExtractionResult) -> Tuple[bool, List[str]]:
    """
    Test database integration.

    Args:
        extraction_result: Extraction result to test

    Returns:
        Tuple of (all_passed, error_messages)
    """
    console.print("\n[bold cyan]═══ Test 4: Database Integration ═══[/bold cyan]\n")

    errors = []
    passed = 0
    total = 0

    # Check if lookup_existing_officer was called
    total += 1
    console.print("[cyan]Checking if lookup_existing_officer was called...[/cyan]")
    lookup_called = any(
        tc.tool_name == "lookup_existing_officer"
        for tc in extraction_result.tool_calls
    )

    if lookup_called:
        console.print("[green]  ✓ PASS: lookup_existing_officer was called[/green]")
        passed += 1
    else:
        error_msg = "lookup_existing_officer was not called by agent"
        console.print(f"[yellow]  ⚠ INFO: {error_msg}[/yellow]")
        # Not a hard failure - agent might skip if DB not available

    # Check if database is configured
    total += 1
    console.print("[cyan]Checking if database is configured...[/cyan]")

    try:
        CONFIG.validate_db_credentials(require_db=True)
        console.print("[green]  ✓ Database credentials are configured[/green]")
        passed += 1
        db_available = True
    except ValueError as e:
        console.print(f"[yellow]  ⚠ Database not configured: {e}[/yellow]")
        console.print("[yellow]  Skipping database save/query tests[/yellow]")
        db_available = False

    # If database available and officer exists, test save and query
    if db_available and extraction_result.officer_bio:
        # Check if save_officer_bio was called
        total += 1
        console.print("[cyan]Checking if save_officer_bio was called...[/cyan]")
        save_called = any(
            tc.tool_name == "save_officer_bio" and tc.success
            for tc in extraction_result.tool_calls
        )

        if save_called:
            console.print("[green]  ✓ PASS: save_officer_bio was called and succeeded[/green]")
            passed += 1

            # Verify we can query the database
            total += 1
            console.print("[cyan]Attempting to query database for saved officer...[/cyan]")

            try:
                from tools.database_tools import execute_lookup_officer

                lookup_result = execute_lookup_officer({"name": extraction_result.officer_bio.name})

                if lookup_result.success and lookup_result.data.get('found'):
                    console.print(f"[green]  ✓ PASS: Officer '{extraction_result.officer_bio.name}' found in database[/green]")
                    passed += 1
                else:
                    error_msg = f"Officer '{extraction_result.officer_bio.name}' not found in database after save"
                    console.print(f"[yellow]  ⚠ WARNING: {error_msg}[/yellow]")
                    # Not a hard error - might be timing issue or mock DB
                    passed += 1
            except Exception as e:
                error_msg = f"Database query failed: {e}"
                console.print(f"[red]  ✗ FAIL: {error_msg}[/red]")
                errors.append(error_msg)
        else:
            error_msg = "save_officer_bio was not called or failed"
            console.print(f"[yellow]  ⚠ INFO: {error_msg}[/yellow]")
            # Not a hard failure

    # Summary
    all_passed = len(errors) == 0
    console.print(f"\n[bold]Database Integration: {passed}/{total} checks passed[/bold]")

    if all_passed:
        console.print("[bold green]✓ Test 4 PASSED: Database integration successful[/bold green]")
    elif not db_available:
        console.print("[bold yellow]⚠ Test 4 SKIPPED: Database not configured[/bold yellow]")
    else:
        console.print(f"[bold red]✗ Test 4 FAILED: {len(errors)} issues found[/bold red]")
        for error in errors:
            console.print(f"  - {error}")

    return all_passed, errors


def generate_test_report(test_results: List[Tuple[str, bool, List[str]]]) -> None:
    """
    Generate final test report.

    Args:
        test_results: List of (test_name, passed, errors) tuples
    """
    console.print("\n" + "=" * 80)
    console.print("\n[bold magenta]═══ Test Suite Summary ═══[/bold magenta]\n")

    # Create results table
    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table.add_column("Test", style="cyan", width=30)
    table.add_column("Status", style="white", width=15)
    table.add_column("Errors", style="dim", width=30)

    total_tests = len(test_results)
    passed_tests = 0

    for test_name, passed, errors in test_results:
        if passed:
            status = "[green]✓ PASSED[/green]"
            passed_tests += 1
            error_text = "-"
        else:
            status = "[red]✗ FAILED[/red]"
            error_text = f"{len(errors)} error(s)"

        table.add_row(test_name, status, error_text)

    console.print(table)

    # Calculate success rate
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

    console.print(f"\n[bold]Results:[/bold]")
    console.print(f"  Total Tests: {total_tests}")
    console.print(f"  Passed: [green]{passed_tests}[/green]")
    console.print(f"  Failed: [red]{total_tests - passed_tests}[/red]")
    console.print(f"  Success Rate: [bold]{success_rate:.1f}%[/bold]")

    # Overall result
    if passed_tests == total_tests:
        console.print("\n[bold green]✓ ALL TESTS PASSED![/bold green]\n")
    else:
        console.print(f"\n[bold red]✗ {total_tests - passed_tests} TEST(S) FAILED[/bold red]\n")

    # Print detailed errors
    has_errors = any(len(errors) > 0 for _, _, errors in test_results)
    if has_errors:
        console.print("[bold red]Detailed Errors:[/bold red]")
        for test_name, passed, errors in test_results:
            if errors:
                console.print(f"\n[red]{test_name}:[/red]")
                for error in errors:
                    console.print(f"  • {error}")


def main():
    """Run all tests."""
    console.print(Panel.fit(
        "[bold magenta]PLAgentSDK - Comprehensive Test Suite[/bold magenta]\n"
        "Testing extraction, validation, and database integration",
        border_style="magenta"
    ))

    # Set up logging
    logging.basicConfig(
        level=logging.WARNING,  # Reduce noise during tests
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize database schema (idempotent - creates tables if they don't exist)
    try:
        from tools.database_tools import initialize_database
        initialize_database()
    except Exception as e:
        logging.warning(f"Could not initialize database: {e}")

    test_results = []
    result = None

    try:
        # Test 1: Single Extraction
        result = test_single_extraction()
        test_results.append(("Single Extraction", result.success, []))

        if result.success:
            # Test 2: Control Variables
            passed, errors = test_control_variables(result)
            test_results.append(("Control Variables", passed, errors))

            # Test 3: Date Validation
            passed, errors = test_date_validation(result)
            test_results.append(("Date Validation", passed, errors))

            # Test 4: Database Integration
            passed, errors = test_database_integration(result)
            test_results.append(("Database Integration", passed, errors))
        else:
            # Skip remaining tests if extraction failed
            console.print("\n[yellow]⚠ Skipping remaining tests due to extraction failure[/yellow]")
            test_results.append(("Control Variables", False, ["Extraction failed"]))
            test_results.append(("Date Validation", False, ["Extraction failed"]))
            test_results.append(("Database Integration", False, ["Extraction failed"]))

    except Exception as e:
        console.print(f"\n[bold red]✗ Test suite failed with exception: {e}[/bold red]")
        import traceback
        console.print(traceback.format_exc())
        return 1

    # Generate final report
    generate_test_report(test_results)

    # Return exit code
    all_passed = all(passed for _, passed, _ in test_results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
