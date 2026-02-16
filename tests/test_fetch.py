#!/usr/bin/env python3
"""
Test script to diagnose fetch_source_content function.

This script directly tests the fetch_source_content() function to verify
it's fetching the correct content from the Xinhua URL.
"""
from fetch_source import fetch_source_content
from pathlib import Path
from rich.console import Console

console = Console()

def main():
    # The actual Xinhua URL from the plan
    url = "https://www.news.cn/20250901/45e0f3a29d2e4b1ba12bbff08c5aec82/c.html"

    console.print("\n[bold cyan]=== Testing fetch_source_content() ===[/bold cyan]\n")
    console.print(f"[bold]URL:[/bold] {url}\n")

    try:
        # Fetch content
        console.print("[yellow]Fetching content...[/yellow]\n")
        content = fetch_source_content(url)

        # Load test_obituary.txt for comparison
        test_file = Path(__file__).resolve().parent.parent / 'data' / 'test_obituary.txt'
        test_content = test_file.read_text(encoding='utf-8')

        # Display results
        console.print(f"\n[bold green]✓ Fetch completed successfully![/bold green]")
        console.print(f"\n[bold]Content length:[/bold] {len(content)} characters")
        console.print(f"[bold]Test file length:[/bold] {len(test_content)} characters")

        # Show preview
        console.print(f"\n[bold cyan]First 300 characters of fetched content:[/bold cyan]")
        console.print(f"[dim]{content[:300]}[/dim]")

        # Critical checks
        console.print("\n[bold cyan]=== Critical Checks ===[/bold cyan]\n")

        # Check 1: Does it match test file?
        matches_test = content.strip() == test_content.strip()
        if matches_test:
            console.print("[bold red]❌ PROBLEM: Fetched content MATCHES test_obituary.txt![/bold red]")
            console.print("[red]This confirms the bug - we're getting test data instead of real content.[/red]")
        else:
            console.print("[bold green]✓ Content does NOT match test_obituary.txt (good!)[/bold green]")

        # Check 2: Contains key indicators from actual source
        console.print("\n[bold]Checking for key content from actual Xinhua article:[/bold]")

        checks = [
            ("厦门", "Death location: Xiamen (厦门)"),
            ("南京军区", "Military region: Nanjing (南京军区)"),
            ("8月18日", "Death date: August 18 (8月18日)"),
            ("享年82岁", "Age at death: 82 years (享年82岁)"),
            ("第十五次全国代表大会", "15th CCP Congress (第十五次全国代表大会)"),
            ("第十一届全国委员会", "11th CPPCC Committee (第十一届全国委员会)"),
            ("2002", "Year 2002 (for 中将 promotion)"),
            ("中将", "Lieutenant General rank (中将)"),
        ]

        found_count = 0
        for keyword, description in checks:
            if keyword in content:
                console.print(f"  [green]✓ Found:[/green] {description}")
                found_count += 1
            else:
                console.print(f"  [red]✗ Missing:[/red] {description}")

        console.print(f"\n[bold]Found {found_count}/{len(checks)} expected indicators[/bold]")

        # Check 3: Contains indicators from test file (should be absent)
        console.print("\n[bold]Checking for test file indicators (should be ABSENT):[/bold]")

        test_checks = [
            ("2023年1月15日", "Test death date (2023-01-15)"),
            ("北京逝世", "Test death location (Beijing)"),
            ("享年80岁", "Test age (80 years)"),
            ("1943年出生", "Test birth year (1943)"),
        ]

        test_found_count = 0
        for keyword, description in test_checks:
            if keyword in content:
                console.print(f"  [red]✗ FOUND (BAD):[/red] {description}")
                test_found_count += 1
            else:
                console.print(f"  [green]✓ Absent (good):[/green] {description}")

        if test_found_count > 0:
            console.print(f"\n[bold red]❌ PROBLEM: Found {test_found_count} test file indicators![/bold red]")
            console.print("[red]This confirms we're getting test data instead of real content.[/red]")
        else:
            console.print("\n[bold green]✓ No test file indicators found (good!)[/bold green]")

        # Summary
        console.print("\n[bold cyan]=== Summary ===[/bold cyan]\n")
        if matches_test or test_found_count > 0:
            console.print("[bold red]🚨 BUG CONFIRMED: fetch_source_content() is returning test data![/bold red]")
            console.print("[yellow]The function is NOT fetching from the actual URL.[/yellow]")
        elif found_count >= 6:
            console.print("[bold green]✓ SUCCESS: Fetched content appears correct![/bold green]")
            console.print("[green]The function is working as expected.[/green]")
        else:
            console.print("[bold yellow]⚠ UNCLEAR: Content doesn't match test file but also missing expected data[/bold yellow]")
            console.print("[yellow]May need to investigate HTML structure or selectors.[/yellow]")

    except Exception as e:
        console.print(f"\n[bold red]❌ Error during fetch:[/bold red] {e}")
        import traceback
        console.print("\n[dim]Traceback:[/dim]")
        console.print(traceback.format_exc())

if __name__ == "__main__":
    main()
