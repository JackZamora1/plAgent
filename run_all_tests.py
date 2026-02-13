#!/usr/bin/env python3
"""
Comprehensive Test Suite Runner for PLA Agent SDK

Runs all tests with detailed reporting:
- Unit tests for tools, schema, validation
- Integration tests for agent and batch processing
- Performance metrics (time, tokens, cost)
- HTML report generation
- System health scoring
- CI/CD compatible

Usage:
    python run_all_tests.py              # Run all tests
    python run_all_tests.py --fast       # Skip slow integration tests
    python run_all_tests.py --verbose    # Verbose output
"""

import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime
import subprocess
import argparse

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import pytest
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError:
    print("Error: Required packages not installed")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)

console = Console()


class TestMetrics:
    """Collect and analyze test metrics."""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.total_tests = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = []
        self.performance_data = {}

    def start(self):
        """Start timing."""
        self.start_time = time.time()

    def finish(self):
        """Finish timing."""
        self.end_time = time.time()

    def get_duration(self) -> float:
        """Get test duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0

    def calculate_health_score(self) -> float:
        """
        Calculate overall system health score (0-100).

        Factors:
        - Pass rate (60% weight)
        - No critical failures (30% weight)
        - Performance within bounds (10% weight)
        """
        if self.total_tests == 0:
            return 0.0

        # Pass rate component (0-60 points)
        pass_rate = (self.passed / self.total_tests) * 60

        # Critical failures component (0-30 points)
        # Deduct points for each error
        critical_score = max(0, 30 - (len(self.errors) * 5))

        # Performance component (0-10 points)
        # Deduct if tests take too long (>5 minutes = slow)
        duration = self.get_duration()
        if duration < 180:  # < 3 minutes = excellent
            perf_score = 10
        elif duration < 300:  # < 5 minutes = good
            perf_score = 7
        elif duration < 600:  # < 10 minutes = acceptable
            perf_score = 5
        else:
            perf_score = 2

        total_score = pass_rate + critical_score + perf_score
        return round(total_score, 1)

    def get_health_status(self) -> tuple[str, str]:
        """Get health status label and color."""
        score = self.calculate_health_score()

        if score >= 90:
            return "EXCELLENT", "green"
        elif score >= 75:
            return "GOOD", "cyan"
        elif score >= 60:
            return "FAIR", "yellow"
        elif score >= 40:
            return "POOR", "orange"
        else:
            return "CRITICAL", "red"


def print_header():
    """Print test suite header."""
    header = """
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║         PLA AGENT SDK - COMPREHENSIVE TEST SUITE     ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    """
    console.print(header, style="bold cyan")
    console.print()


def discover_tests() -> dict:
    """
    Discover all test files and categorize them.

    Returns:
        Dictionary mapping test categories to file paths
    """
    test_dir = Path(__file__).parent

    tests = {
        "unit": {
            "schema": test_dir / "test_schema.py",
            "config": test_dir / "test_config.py",
            "tool_registry": test_dir / "test_tool_registry.py",
        },
        "validation": {
            "validation_tools": test_dir / "test_validation_tools.py",
            "database_tools": test_dir / "test_database_tools.py",
        },
        "integration": {
            "agent": test_dir / "test_agent.py",
            "anthropic_tools": test_dir / "test_anthropic_tools.py",
            "workflow": test_dir / "test_workflow.py",
        },
        "batch": {
            "batch_processor": test_dir / "test_batch_processor.py",
        }
    }

    # Verify test files exist
    all_tests = []
    for category, test_files in tests.items():
        for name, path in test_files.items():
            if path.exists():
                all_tests.append(str(path))
            else:
                console.print(f"[yellow]Warning: Test file not found: {path}[/yellow]")

    return tests, all_tests


def run_pytest_suite(test_files: list, fast_mode: bool = False, verbose: bool = False) -> tuple:
    """
    Run pytest test suite.

    Args:
        test_files: List of test file paths
        fast_mode: Skip slow integration tests
        verbose: Verbose output

    Returns:
        Tuple of (exit_code, metrics)
    """
    metrics = TestMetrics()
    metrics.start()

    # Prepare pytest arguments
    pytest_args = [
        "-v" if verbose else "-q",
        "--tb=short",
        "--strict-markers",
        "--disable-warnings",
        f"--html=test_results.html",
        "--self-contained-html",
        "--json-report",
        "--json-report-file=test_results.json",
    ]

    # Add markers for fast mode
    if fast_mode:
        pytest_args.append("-m")
        pytest_args.append("not slow")

    # Add test files
    pytest_args.extend(test_files)

    console.print("[cyan]Running pytest test suite...[/cyan]\n")

    # Run pytest
    try:
        exit_code = pytest.main(pytest_args)

        metrics.finish()

        # Load test results from JSON report
        json_report_path = Path("test_results.json")
        if json_report_path.exists():
            with open(json_report_path, 'r') as f:
                report_data = json.load(f)

            summary = report_data.get('summary', {})
            metrics.total_tests = summary.get('total', 0)
            metrics.passed = summary.get('passed', 0)
            metrics.failed = summary.get('failed', 0)
            metrics.skipped = summary.get('skipped', 0)

            # Collect errors
            for test in report_data.get('tests', []):
                if test.get('outcome') in ['failed', 'error']:
                    metrics.errors.append({
                        'name': test.get('nodeid', 'unknown'),
                        'message': test.get('call', {}).get('longrepr', 'No message'),
                    })

        return exit_code, metrics

    except Exception as e:
        console.print(f"[red]Error running tests: {e}[/red]")
        metrics.finish()
        return 1, metrics


def display_test_summary(metrics: TestMetrics):
    """Display comprehensive test summary."""
    console.print()
    console.print("[bold magenta]" + "═" * 70 + "[/bold magenta]")
    console.print("[bold white]TEST SUMMARY[/bold white]")
    console.print("[bold magenta]" + "═" * 70 + "[/bold magenta]")
    console.print()

    # Overall statistics
    stats_table = Table(
        title="Overall Statistics",
        show_header=True,
        header_style="bold cyan",
        box=box.ROUNDED
    )
    stats_table.add_column("Metric", style="cyan", width=30)
    stats_table.add_column("Value", style="white", width=20)

    stats_table.add_row("Total Tests", str(metrics.total_tests))
    stats_table.add_row(
        "Passed",
        f"[green]{metrics.passed}[/green]"
    )
    stats_table.add_row(
        "Failed",
        f"[red]{metrics.failed}[/red]" if metrics.failed > 0 else "0"
    )
    stats_table.add_row(
        "Skipped",
        f"[yellow]{metrics.skipped}[/yellow]" if metrics.skipped > 0 else "0"
    )

    if metrics.total_tests > 0:
        pass_rate = (metrics.passed / metrics.total_tests) * 100
        stats_table.add_row("Pass Rate", f"{pass_rate:.1f}%")

    stats_table.add_row("Duration", f"{metrics.get_duration():.2f}s")

    console.print(stats_table)
    console.print()

    # Health score
    health_score = metrics.calculate_health_score()
    health_status, health_color = metrics.get_health_status()

    health_panel = Panel(
        f"[bold {health_color}]{health_score}/100[/bold {health_color}]\n"
        f"[{health_color}]Status: {health_status}[/{health_color}]",
        title="System Health Score",
        border_style=health_color,
        padding=(1, 2)
    )
    console.print(health_panel)
    console.print()

    # Errors (if any)
    if metrics.errors:
        console.print("[bold red]Failed Tests:[/bold red]\n")

        error_table = Table(show_header=True, header_style="bold red", box=box.ROUNDED)
        error_table.add_column("Test", style="red", width=50)
        error_table.add_column("Error", style="dim", width=50)

        for error in metrics.errors[:10]:  # Show first 10 errors
            test_name = error['name'].split("::")[-1]  # Just the test name
            error_msg = str(error['message'])[:80]  # Truncate long messages
            error_table.add_row(test_name, error_msg)

        if len(metrics.errors) > 10:
            error_table.add_row(
                "[dim]...[/dim]",
                f"[dim]+{len(metrics.errors) - 10} more errors[/dim]"
            )

        console.print(error_table)
        console.print()

    # Output files
    console.print("[cyan]Generated Reports:[/cyan]")
    console.print("  [green]✓[/green] test_results.html - Detailed HTML report")
    console.print("  [green]✓[/green] test_results.json - JSON test data")
    console.print()


def generate_enhanced_html_report():
    """
    Enhance the pytest HTML report with custom styling and health score.
    """
    html_path = Path("test_results.html")

    if not html_path.exists():
        return

    try:
        # Read existing HTML
        html_content = html_path.read_text(encoding='utf-8')

        # Calculate metrics from JSON report
        json_path = Path("test_results.json")
        if json_path.exists():
            with open(json_path, 'r') as f:
                report_data = json.load(f)

            metrics = TestMetrics()
            summary = report_data.get('summary', {})
            metrics.total_tests = summary.get('total', 0)
            metrics.passed = summary.get('passed', 0)
            metrics.failed = summary.get('failed', 0)
            metrics.duration = report_data.get('duration', 0)

            health_score = metrics.calculate_health_score()
            health_status, _ = metrics.get_health_status()

            # Add custom header with health score
            custom_header = f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white; padding: 30px; margin: -8px -8px 20px -8px;
                        border-radius: 0;">
                <h1 style="margin: 0; font-size: 32px;">PLA Agent SDK - Test Results</h1>
                <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">
                    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
                <div style="margin-top: 20px; background: rgba(255,255,255,0.1);
                            padding: 20px; border-radius: 10px;">
                    <div style="font-size: 48px; font-weight: bold;">{health_score}/100</div>
                    <div style="font-size: 18px; margin-top: 5px;">
                        System Health: {health_status}
                    </div>
                    <div style="margin-top: 15px; font-size: 14px; opacity: 0.9;">
                        {metrics.passed}/{metrics.total_tests} tests passed •
                        {metrics.failed} failed •
                        {metrics.duration:.1f}s duration
                    </div>
                </div>
            </div>
            """

            # Insert custom header after <body> tag
            html_content = html_content.replace(
                '<body>',
                f'<body>{custom_header}'
            )

            # Write enhanced HTML
            html_path.write_text(html_content, encoding='utf-8')

            console.print("[green]✓ Enhanced HTML report with health score[/green]")

    except Exception as e:
        console.print(f"[yellow]Warning: Could not enhance HTML report: {e}[/yellow]")


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(
        description='Run comprehensive PLA Agent SDK test suite'
    )
    parser.add_argument(
        '--fast',
        action='store_true',
        help='Skip slow integration tests'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--category', '-c',
        choices=['unit', 'validation', 'integration', 'batch', 'all'],
        default='all',
        help='Run specific test category'
    )
    parser.add_argument(
        '--ci',
        action='store_true',
        help='CI/CD mode (minimal output, strict exit codes)'
    )

    args = parser.parse_args()

    # Print header (unless in CI mode)
    if not args.ci:
        print_header()

    # Discover tests
    console.print("[cyan]Discovering test files...[/cyan]")
    test_categories, all_test_files = discover_tests()

    # Select tests based on category
    if args.category == 'all':
        selected_tests = all_test_files
    else:
        selected_tests = []
        for test_name, test_path in test_categories.get(args.category, {}).items():
            if test_path.exists():
                selected_tests.append(str(test_path))

    console.print(f"[green]Found {len(selected_tests)} test file(s)[/green]\n")

    if not selected_tests:
        console.print("[red]No tests found![/red]")
        return 1

    # Display test plan (unless in CI mode)
    if not args.ci:
        plan_table = Table(
            title="Test Execution Plan",
            show_header=True,
            header_style="bold cyan",
            box=box.ROUNDED
        )
        plan_table.add_column("Category", style="cyan", width=20)
        plan_table.add_column("Tests", style="white", width=50)

        for category, tests in test_categories.items():
            if args.category != 'all' and args.category != category:
                continue

            test_names = []
            for name, path in tests.items():
                if path.exists():
                    test_names.append(f"✓ {name}")
                else:
                    test_names.append(f"✗ {name} (missing)")

            plan_table.add_row(category.title(), "\n".join(test_names))

        console.print(plan_table)
        console.print()

        if args.fast:
            console.print("[yellow]Fast mode: Skipping slow integration tests[/yellow]\n")

        time.sleep(1)

    # Run tests
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        if not args.ci:
            task = progress.add_task("[cyan]Running tests...", total=None)

        exit_code, metrics = run_pytest_suite(
            selected_tests,
            fast_mode=args.fast,
            verbose=args.verbose
        )

        if not args.ci:
            if exit_code == 0:
                progress.update(task, description="[green]✓ All tests passed![/green]")
            else:
                progress.update(task, description="[red]✗ Some tests failed[/red]")

    # Display summary (unless in CI mode with failures)
    if not args.ci or exit_code == 0:
        display_test_summary(metrics)

    # Enhance HTML report
    if not args.ci:
        generate_enhanced_html_report()

    # CI/CD mode output
    if args.ci:
        # Print minimal JSON output for CI systems
        ci_output = {
            "success": exit_code == 0,
            "total_tests": metrics.total_tests,
            "passed": metrics.passed,
            "failed": metrics.failed,
            "skipped": metrics.skipped,
            "duration": metrics.get_duration(),
            "health_score": metrics.calculate_health_score(),
            "health_status": metrics.get_health_status()[0],
        }
        print(json.dumps(ci_output, indent=2))

    # Exit with appropriate code
    if exit_code != 0:
        console.print("\n[red]❌ Tests failed - see test_results.html for details[/red]\n")
        return 1
    else:
        if not args.ci:
            console.print("\n[bold green]✅ All tests passed![/bold green]\n")
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Tests interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)
