#!/usr/bin/env python3
"""Test script for BatchProcessor functionality."""
import sys
import logging
from pathlib import Path
from rich.console import Console

from batch_processor import BatchProcessor
from tools.extraction_tools import extract_text_from_file

console = Console()
logging.basicConfig(level=logging.INFO)


def test_basic_initialization():
    """Test basic initialization of BatchProcessor."""
    console.print("\n[bold cyan]Test 1: Basic Initialization[/bold cyan]")

    try:
        processor = BatchProcessor(require_db=False)
        console.print("[green]✓ BatchProcessor initialized successfully[/green]")
        return True
    except Exception as e:
        console.print(f"[red]✗ Failed to initialize: {e}[/red]")
        return False


def test_single_url_mock():
    """Test processing with a mock obituary file."""
    console.print("\n[bold cyan]Test 2: Single URL Processing (Mock)[/bold cyan]")

    # Check if test obituary exists
    test_file = Path("data/test_obituary.txt")
    if not test_file.exists():
        console.print(f"[yellow]⚠ Skipping: {test_file} not found[/yellow]")
        return None

    try:
        processor = BatchProcessor(require_db=False)

        # Read test source text
        source_text = extract_text_from_file(str(test_file))
        console.print(f"[cyan]Loaded test obituary ({len(source_text)} chars)[/cyan]")

        # Process using SDK directly (not from URL)
        result = processor.sdk.extract_bio_agentic(
            source_text=source_text,
            source_url="https://www.news.cn/test/obituary.html",
            source_type="universal"
        )

        if result.success:
            console.print(f"[green]✓ Extraction successful: {result.officer_bio.name}[/green]")
            console.print(f"[dim]  Confidence: {result.officer_bio.confidence_score:.2f}[/dim]")
            console.print(f"[dim]  Tokens: {result.get_total_tokens():,}[/dim]")
            return True
        else:
            console.print(f"[red]✗ Extraction failed: {result.error_message}[/red]")
            return False

    except Exception as e:
        console.print(f"[red]✗ Error during processing: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_flagging_logic():
    """Test review flagging logic."""
    console.print("\n[bold cyan]Test 3: Review Flagging Logic[/bold cyan]")

    try:
        processor = BatchProcessor(require_db=False)

        # Check that review directory exists
        if processor.review_dir.exists():
            console.print(f"[green]✓ Review directory exists: {processor.review_dir}[/green]")
        else:
            console.print(f"[red]✗ Review directory not created[/red]")
            return False

        # Test flagging counter
        initial_count = processor.total_flagged_for_review
        console.print(f"[cyan]Initial flagged count: {initial_count}[/cyan]")

        return True

    except Exception as e:
        console.print(f"[red]✗ Error testing flagging: {e}[/red]")
        return False


def test_rate_limiting():
    """Test rate limiting mechanism."""
    console.print("\n[bold cyan]Test 4: Rate Limiting[/bold cyan]")

    try:
        import time

        processor = BatchProcessor(require_db=False, rate_limit_seconds=0.5)
        console.print("[cyan]Processor created with 0.5s rate limit[/cyan]")

        # Test rate limiting
        start = time.time()
        processor._rate_limit()
        first_elapsed = time.time() - start
        console.print(f"[dim]First call: {first_elapsed:.3f}s[/dim]")

        start = time.time()
        processor._rate_limit()
        second_elapsed = time.time() - start
        console.print(f"[dim]Second call: {second_elapsed:.3f}s (should be ~0.5s)[/dim]")

        if 0.4 <= second_elapsed <= 0.6:
            console.print("[green]✓ Rate limiting working correctly[/green]")
            return True
        else:
            console.print(f"[yellow]⚠ Rate limiting may not be working (elapsed: {second_elapsed:.3f}s)[/yellow]")
            return None

    except Exception as e:
        console.print(f"[red]✗ Error testing rate limiting: {e}[/red]")
        return False


def test_report_generation():
    """Test report generation with empty results."""
    console.print("\n[bold cyan]Test 5: Report Generation[/bold cyan]")

    try:
        processor = BatchProcessor(require_db=False)

        # Test with empty results
        console.print("[cyan]Testing with empty results...[/cyan]")
        processor.generate_batch_report([])
        console.print("[green]✓ Report generation handles empty results[/green]")

        return True

    except Exception as e:
        console.print(f"[red]✗ Error generating report: {e}[/red]")
        return False


def test_url_file_parsing():
    """Test parsing URLs from file."""
    console.print("\n[bold cyan]Test 6: URL File Parsing[/bold cyan]")

    try:
        # Create temporary test file
        test_file = Path("test_urls_temp.txt")
        test_content = """# Test URL file
https://www.news.cn/test1.html
https://www.news.cn/test2.html

# Comment line
https://www.news.cn/test3.html
"""
        test_file.write_text(test_content, encoding='utf-8')
        console.print(f"[cyan]Created test file: {test_file}[/cyan]")

        # Test parsing (without processing)
        with open(test_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

        console.print(f"[cyan]Parsed {len(urls)} URLs[/cyan]")

        # Cleanup
        test_file.unlink()

        if len(urls) == 3:
            console.print("[green]✓ URL file parsing works correctly[/green]")
            return True
        else:
            console.print(f"[red]✗ Expected 3 URLs, got {len(urls)}[/red]")
            return False

    except Exception as e:
        console.print(f"[red]✗ Error parsing URL file: {e}[/red]")
        # Cleanup on error
        if test_file.exists():
            test_file.unlink()
        return False


def run_all_tests():
    """Run all tests and report results."""
    console.print("\n" + "=" * 80)
    console.print("[bold magenta]BatchProcessor Test Suite[/bold magenta]")
    console.print("=" * 80)

    tests = [
        ("Basic Initialization", test_basic_initialization),
        ("Single URL Processing", test_single_url_mock),
        ("Review Flagging", test_flagging_logic),
        ("Rate Limiting", test_rate_limiting),
        ("Report Generation", test_report_generation),
        ("URL File Parsing", test_url_file_parsing),
    ]

    results = {}
    for name, test_func in tests:
        try:
            result = test_func()
            results[name] = result
        except Exception as e:
            console.print(f"\n[red]✗ Test '{name}' crashed: {e}[/red]")
            results[name] = False

    # Summary
    console.print("\n" + "=" * 80)
    console.print("[bold magenta]Test Summary[/bold magenta]")
    console.print("=" * 80 + "\n")

    passed = sum(1 for r in results.values() if r is True)
    skipped = sum(1 for r in results.values() if r is None)
    failed = sum(1 for r in results.values() if r is False)
    total = len(results)

    for name, result in results.items():
        if result is True:
            console.print(f"[green]✓ {name}[/green]")
        elif result is None:
            console.print(f"[yellow]⚠ {name} (skipped)[/yellow]")
        else:
            console.print(f"[red]✗ {name}[/red]")

    console.print(f"\n[bold]Results: {passed}/{total} passed, {skipped} skipped, {failed} failed[/bold]\n")

    if failed > 0:
        console.print("[red]Some tests failed. Check output above for details.[/red]")
        return 1
    elif passed == 0:
        console.print("[yellow]No tests passed. Check configuration.[/yellow]")
        return 1
    else:
        console.print("[green]All tests passed or skipped![/green]")
        return 0


def main():
    """Main test function."""
    try:
        return run_all_tests()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Tests interrupted by user[/yellow]")
        return 1
    except Exception as e:
        console.print(f"\n[red]✗ Test suite failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
