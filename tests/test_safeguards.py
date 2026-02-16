#!/usr/bin/env python3
"""
Test script to verify extraction safeguards are working.

This script tests that:
1. Source validation rejects test_obituary.txt content
2. URL validation rejects placeholder URLs
"""
from agent import PLAgentSDK
from tools.extraction_tools import execute_save_officer_bio
from pathlib import Path
from rich.console import Console

console = Console()

def test_source_validation():
    """Test that agent rejects test_obituary.txt content."""
    console.print("\n[bold cyan]=== Test 1: Source Validation ===[/bold cyan]\n")

    # Load test_obituary.txt content
    test_file = Path("data/test_obituary.txt")
    if not test_file.exists():
        console.print("[yellow]⚠ test_obituary.txt not found, skipping test[/yellow]")
        return False

    test_content = test_file.read_text(encoding='utf-8')

    # Try to extract with test content
    agent = PLAgentSDK()

    try:
        result = agent.extract_bio_agentic(
            source_text=test_content,
            source_url="https://www.news.cn/20250901/45e0f3a29d2e4b1ba12bbff08c5aec82/c.html")
        console.print("[red]❌ FAIL: Agent did not reject test content[/red]")
        return False

    except ValueError as e:
        if "test_obituary.txt" in str(e):
            console.print("[green]✓ PASS: Agent correctly rejected test_obituary.txt content[/green]")
            console.print(f"[dim]Error message: {str(e)[:100]}...[/dim]")
            return True
        else:
            console.print(f"[red]❌ FAIL: Wrong error: {e}[/red]")
            return False

    except Exception as e:
        console.print(f"[red]❌ FAIL: Unexpected error: {e}[/red]")
        return False


def test_url_validation():
    """Test that save_officer_bio rejects placeholder URLs."""
    console.print("\n[bold cyan]=== Test 2: URL Validation ===[/bold cyan]\n")

    # Test data with placeholder URL
    test_input = {
        "name": "林炳尧",
        "source_url": "https://example.com/test",
        "source_type": "obituary",
        "birth_date": "1943",
        "death_date": "2023-01-15",
        "promotions": [{"rank": "少将", "date": "1995"}],
        "confidence_score": 0.95
    }

    result = execute_save_officer_bio(test_input)

    if not result.success:
        if "placeholder" in result.error.lower() or "example.com" in result.error.lower():
            console.print("[green]✓ PASS: Tool correctly rejected placeholder URL[/green]")
            console.print(f"[dim]Error message: {result.error[:100]}...[/dim]")
            return True
        else:
            console.print(f"[yellow]⚠ PARTIAL: Tool failed but with different error: {result.error}[/yellow]")
            return False
    else:
        console.print("[red]❌ FAIL: Tool did not reject placeholder URL[/red]")
        return False


def test_real_url_passes():
    """Test that real URLs are accepted."""
    console.print("\n[bold cyan]=== Test 3: Real URL Acceptance ===[/bold cyan]\n")

    # Test data with real URL
    test_input = {
        "name": "林炳尧",
        "source_url": "https://www.news.cn/20250901/45e0f3a29d2e4b1ba12bbff08c5aec82/c.html",
        "source_type": "obituary",
        "birth_date": "1943",
        "death_date": "2023-01-15",
        "promotions": [{"rank": "少将", "date": "1995"}],
        "confidence_score": 0.95
    }

    result = execute_save_officer_bio(test_input)

    if result.success:
        console.print("[green]✓ PASS: Tool correctly accepted real URL[/green]")
        return True
    else:
        console.print(f"[red]❌ FAIL: Tool rejected real URL: {result.error}[/red]")
        return False


def main():
    console.print("\n[bold cyan]╔════════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║  Testing Extraction Safeguards         ║[/bold cyan]")
    console.print("[bold cyan]╚════════════════════════════════════════╝[/bold cyan]\n")

    results = []

    # Run tests
    results.append(("Source Validation", test_source_validation()))
    results.append(("URL Validation", test_url_validation()))
    results.append(("Real URL Acceptance", test_real_url_passes()))

    # Summary
    console.print("\n[bold cyan]=== Test Summary ===[/bold cyan]\n")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[green]✓ PASS[/green]" if result else "[red]✗ FAIL[/red]"
        console.print(f"  {status}  {test_name}")

    console.print(f"\n[bold]Results: {passed}/{total} tests passed[/bold]")

    if passed == total:
        console.print("\n[bold green]🎉 All safeguards working correctly![/bold green]")
        return 0
    else:
        console.print("\n[bold red]⚠️  Some safeguards failed - please investigate[/bold red]")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
