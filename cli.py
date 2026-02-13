#!/usr/bin/env python3
"""
PLA Agent SDK - Command Line Interface

Full-featured CLI for extracting PLA officer biographies from obituaries.
"""
import sys
import argparse
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from collections import Counter

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.progress import track
from rich import box
from rich.logging import RichHandler
from rich.prompt import Prompt
from rich.live import Live
from rich.spinner import Spinner

from agent import PLAgentSDK, ConversationPrinter
from batch_processor import BatchProcessor
from schema import AgentExtractionResult, OfficerBio
from tools.extraction_tools import extract_text_from_file
from config import CONFIG

console = Console()


def setup_logging(verbose: bool = False, debug: bool = False):
    """
    Set up logging configuration.

    Args:
        verbose: Enable verbose logging
        debug: Enable debug logging
    """
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING

    logging.basicConfig(
        level=level,
        format='%(message)s',
        handlers=[RichHandler(console=console, rich_tracebacks=True)]
    )


def print_header(title: str, subtitle: str = ""):
    """Print formatted header."""
    text = f"[bold magenta]{title}[/bold magenta]"
    if subtitle:
        text += f"\n{subtitle}"
    console.print(Panel.fit(text, border_style="magenta"))


def print_error(message: str):
    """Print error message."""
    console.print(f"[bold red]✗ Error:[/bold red] {message}")


def print_success(message: str):
    """Print success message."""
    console.print(f"[bold green]✓[/bold green] {message}")


def print_warning(message: str):
    """Print warning message."""
    console.print(f"[bold yellow]⚠[/bold yellow] {message}")


# ============================================================================
# Command: extract
# ============================================================================

def cmd_extract(args):
    """
    Extract biography from single URL.

    Args:
        args: Parsed command-line arguments
    """
    print_header("Extract PLA Officer Biography", f"URL: {args.url}")

    logger = logging.getLogger(__name__)

    try:
        # Initialize SDK
        console.print("\n[cyan]Initializing SDK...[/cyan]")
        sdk = PLAgentSDK(require_db=args.save_db)
        print_success("SDK initialized")

        # Fetch source content
        console.print(f"\n[cyan]Fetching content from URL...[/cyan]")
        from fetch_source import fetch_source_content
        source_text = fetch_source_content(args.url)

        if not source_text:
            print_error("Failed to fetch content from URL")
            return 1

        print_success(f"Fetched {len(source_text)} characters")

        # Extract biography (universal profile - Claude will identify source type)
        console.print(f"\n[cyan]Extracting biography...[/cyan]")
        console.print(f"[dim]Using universal extraction (Claude will adapt to source type)[/dim]")
        result = sdk.extract_bio_agentic(
            source_text=source_text,
            source_url=args.url,
            source_type="universal"
        )

        # Check result
        if not result.success:
            print_error(f"Extraction failed: {result.error_message}")
            return 1

        print_success(f"Successfully extracted: {result.officer_bio.name}")

        # Show details
        officer = result.officer_bio
        console.print("\n[bold cyan]Extracted Information:[/bold cyan]")

        info_table = Table(show_header=False, box=box.SIMPLE)
        info_table.add_column("Field", style="cyan", width=25)
        info_table.add_column("Value", style="white", width=50)

        info_table.add_row("Name", officer.name)
        if officer.pinyin_name:
            info_table.add_row("Pinyin", officer.pinyin_name)
        if officer.hometown:
            info_table.add_row("Hometown", officer.hometown)
        if officer.birth_date:
            info_table.add_row("Birth Date", officer.birth_date)
        if officer.death_date:
            info_table.add_row("Death Date", officer.death_date)
        info_table.add_row("Confidence", f"{officer.confidence_score:.2f}")

        console.print(info_table)

        # Show performance metrics
        console.print("\n[bold cyan]Performance Metrics:[/bold cyan]")
        metrics_table = Table(show_header=False, box=box.SIMPLE)
        metrics_table.add_column("Metric", style="cyan", width=25)
        metrics_table.add_column("Value", style="white", width=20)

        metrics_table.add_row("Conversation Turns", str(result.conversation_turns))
        metrics_table.add_row("Tool Calls", str(len(result.tool_calls)))
        metrics_table.add_row("Input Tokens", f"{result.total_input_tokens:,}")
        metrics_table.add_row("Output Tokens", f"{result.total_output_tokens:,}")
        metrics_table.add_row("Total Tokens", f"{result.get_total_tokens():,}")

        console.print(metrics_table)

        # Save to file
        output_file = sdk.save_result_to_file(result)
        print_success(f"Saved to: {output_file}")

        # Save to database if requested
        if args.save_db and officer.confidence_score >= 0.8:
            try:
                from tools.database_tools import save_officer_bio_to_database
                db_result = save_officer_bio_to_database(officer)
                if db_result:
                    print_success(f"Saved to database")
                else:
                    print_warning("Database save failed")
            except Exception as e:
                print_error(f"Database error: {e}")

        # Show verbose conversation if requested
        if args.verbose:
            console.print("\n[bold cyan]Conversation Detail:[/bold cyan]\n")
            # Get messages from SDK's last conversation
            if hasattr(sdk, '_last_messages'):
                ConversationPrinter.print_conversation(sdk._last_messages)

        return 0

    except KeyboardInterrupt:
        print_warning("Interrupted by user")
        return 1
    except Exception as e:
        print_error(f"Extraction failed: {e}")
        logger.exception("Extraction error")
        return 1


# ============================================================================
# Command: batch
# ============================================================================

def cmd_batch(args):
    """
    Process multiple URLs from file.

    Args:
        args: Parsed command-line arguments
    """
    print_header("Batch Processing", f"File: {args.file}")

    logger = logging.getLogger(__name__)

    try:
        # Check file exists
        if not Path(args.file).exists():
            print_error(f"File not found: {args.file}")
            return 1

        # Initialize processor
        console.print("\n[cyan]Initializing BatchProcessor...[/cyan]")
        processor = BatchProcessor(
            require_db=args.save_db,
            rate_limit_seconds=args.rate_limit
        )
        print_success("Processor initialized")

        # Handle parallelism
        if args.parallel and args.parallel > 1:
            print_warning(f"Parallel processing ({args.parallel} workers) not yet implemented")
            print_warning("Processing sequentially instead")
            # TODO: Implement parallel processing

        # Process URLs with universal extraction (Claude adapts to each source)
        console.print(f"[dim]Using universal extraction - Claude will adapt to each source type[/dim]")
        results = processor.process_from_file(args.file, save_to_db=args.save_db,
                                             source_type="universal")

        if not results:
            print_warning("No results to process")
            return 1

        # Generate report
        processor.generate_batch_report(results)

        # Show summary
        successful = sum(1 for r in results if r.success)
        console.print(f"\n[bold green]✓ Processed {len(results)} URLs[/bold green]")
        console.print(f"  Successful: {successful}")
        console.print(f"  Failed: {len(results) - successful}")
        console.print(f"  Flagged for review: {processor.total_flagged_for_review}")

        return 0

    except KeyboardInterrupt:
        print_warning("Interrupted by user")
        return 1
    except Exception as e:
        print_error(f"Batch processing failed: {e}")
        logger.exception("Batch processing error")
        return 1


# ============================================================================
# Command: test
# ============================================================================

def cmd_test(args):
    """
    Run test suite.

    Args:
        args: Parsed command-line arguments
    """
    print_header("Test Suite", "Running extraction tests")

    logger = logging.getLogger(__name__)

    try:
        # Determine test file
        if args.obituary:
            test_file = Path(args.obituary)
            if not test_file.exists():
                print_error(f"Test file not found: {test_file}")
                return 1
        else:
            test_file = Path("data/test_obituary.txt")
            if not test_file.exists():
                print_error("Default test file not found: data/test_obituary.txt")
                return 1

        console.print(f"\n[cyan]Using test file: {test_file}[/cyan]")

        # Load obituary
        source_text = extract_text_from_file(str(test_file))
        print_success(f"Loaded {len(source_text)} characters")

        # Initialize SDK
        console.print("\n[cyan]Initializing SDK...[/cyan]")
        sdk = PLAgentSDK(require_db=False)
        print_success("SDK initialized")

        # Run extraction
        console.print("\n[cyan]Running extraction test...[/cyan]")
        console.print("[dim]Using universal extraction (Claude adapts to source)[/dim]")
        result = sdk.extract_bio_agentic(
            source_text=source_text,
            source_url="https://test/obituary.html",
            source_type="universal"
        )

        # Analyze results
        console.print("\n[bold cyan]Test Results:[/bold cyan]\n")

        tests = []

        # Test 1: Extraction succeeded
        tests.append(("Extraction Success", result.success, None))

        if result.success and result.officer_bio:
            officer = result.officer_bio

            # Test 2: Has required fields
            has_required = bool(officer.name and officer.source_url)
            tests.append(("Required Fields", has_required, "name, source_url"))

            # Test 3: Confidence score
            good_confidence = officer.confidence_score >= 0.8
            tests.append((
                "Confidence Score",
                good_confidence,
                f"{officer.confidence_score:.2f} {'≥' if good_confidence else '<'} 0.8"
            ))

            # Test 4: Has biographical data
            has_bio_data = any([
                officer.birth_date,
                officer.enlistment_date,
                officer.promotions,
                officer.notable_positions
            ])
            tests.append(("Biographical Data", has_bio_data, None))

            # Test 5: Tool usage
            tool_count = len(result.tool_calls)
            good_tools = tool_count >= 3
            tests.append((
                "Tool Usage",
                good_tools,
                f"{tool_count} tools used"
            ))

            # Test 6: Token efficiency
            total_tokens = result.get_total_tokens()
            efficient = total_tokens < 100000
            tests.append((
                "Token Efficiency",
                efficient,
                f"{total_tokens:,} tokens"
            ))

        else:
            # If extraction failed, mark all other tests as failed
            for test_name in [
                "Required Fields",
                "Confidence Score",
                "Biographical Data",
                "Tool Usage",
                "Token Efficiency"
            ]:
                tests.append((test_name, False, result.error_message))

        # Display test results
        test_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
        test_table.add_column("Test", style="cyan", width=25)
        test_table.add_column("Status", style="white", width=10)
        test_table.add_column("Details", style="dim", width=40)

        for test_name, passed, details in tests:
            status = "[green]✓ PASS[/green]" if passed else "[red]✗ FAIL[/red]"
            test_table.add_row(test_name, status, details or "")

        console.print(test_table)

        # Summary
        passed_count = sum(1 for _, passed, _ in tests if passed)
        total_count = len(tests)

        console.print(f"\n[bold]Results: {passed_count}/{total_count} tests passed[/bold]")

        if passed_count == total_count:
            print_success("All tests passed!")
            return 0
        else:
            print_warning(f"{total_count - passed_count} test(s) failed")
            return 1

    except KeyboardInterrupt:
        print_warning("Interrupted by user")
        return 1
    except Exception as e:
        print_error(f"Test failed: {e}")
        logger.exception("Test error")
        return 1


# ============================================================================
# Command: validate
# ============================================================================

def cmd_validate(args):
    """
    Re-run validation on saved extraction.

    Args:
        args: Parsed command-line arguments
    """
    print_header("Validate Extraction", f"File: {args.json}")

    logger = logging.getLogger(__name__)

    try:
        # Load JSON file
        json_path = Path(args.json)
        if not json_path.exists():
            print_error(f"File not found: {args.json}")
            return 1

        console.print(f"\n[cyan]Loading extraction from {json_path}...[/cyan]")
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Parse officer bio
        if 'officer_bio' not in data:
            print_error("Invalid extraction file: missing 'officer_bio'")
            return 1

        officer = OfficerBio(**data['officer_bio'])
        print_success(f"Loaded extraction for: {officer.name}")

        # Re-run validation
        console.print("\n[cyan]Running validation...[/cyan]")

        validation_results = []

        # Validate required fields
        has_required = bool(officer.name and officer.source_url)
        validation_results.append(("Required Fields", has_required, "name, source_url present"))

        # Validate date format
        date_fields = [
            ('birth_date', officer.birth_date),
            ('death_date', officer.death_date),
            ('enlistment_date', officer.enlistment_date),
            ('party_membership_date', officer.party_membership_date),
        ]

        valid_dates = True
        invalid_dates = []
        for field_name, date_value in date_fields:
            if date_value:
                # Check format (YYYY or YYYY-MM-DD)
                import re
                if not (re.match(r'^\d{4}$', date_value) or re.match(r'^\d{4}-\d{2}-\d{2}$', date_value)):
                    valid_dates = False
                    invalid_dates.append(f"{field_name}={date_value}")

        validation_results.append((
            "Date Format",
            valid_dates,
            "All valid" if valid_dates else f"Invalid: {', '.join(invalid_dates)}"
        ))

        # Validate confidence score
        valid_confidence = 0.0 <= officer.confidence_score <= 1.0
        validation_results.append((
            "Confidence Score",
            valid_confidence,
            f"{officer.confidence_score:.2f} in range [0.0, 1.0]"
        ))

        # Validate promotions
        valid_promotions = True
        if officer.promotions:
            for i, promo in enumerate(officer.promotions):
                if not promo.rank:
                    valid_promotions = False

        validation_results.append((
            "Promotions",
            valid_promotions,
            f"{len(officer.promotions) if officer.promotions else 0} promotions"
        ))

        # Display validation results
        console.print("\n[bold cyan]Validation Results:[/bold cyan]\n")

        val_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
        val_table.add_column("Check", style="cyan", width=25)
        val_table.add_column("Status", style="white", width=10)
        val_table.add_column("Details", style="dim", width=40)

        for check_name, passed, details in validation_results:
            status = "[green]✓ PASS[/green]" if passed else "[red]✗ FAIL[/red]"
            val_table.add_row(check_name, status, details)

        console.print(val_table)

        # Summary
        passed_count = sum(1 for _, passed, _ in validation_results if passed)
        total_count = len(validation_results)

        console.print(f"\n[bold]Results: {passed_count}/{total_count} checks passed[/bold]")

        if passed_count == total_count:
            print_success("All validation checks passed!")
            return 0
        else:
            print_warning(f"{total_count - passed_count} validation(s) failed")
            return 1

    except Exception as e:
        print_error(f"Validation failed: {e}")
        logger.exception("Validation error")
        return 1


# ============================================================================
# Command: replay
# ============================================================================

def cmd_replay(args):
    """
    Replay saved extraction conversation.

    Args:
        args: Parsed command-line arguments
    """
    print_header("Replay Conversation", f"File: {args.json}")

    logger = logging.getLogger(__name__)

    try:
        # Load JSON file
        json_path = Path(args.json)
        if not json_path.exists():
            print_error(f"File not found: {args.json}")
            return 1

        console.print(f"\n[cyan]Loading extraction from {json_path}...[/cyan]")
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Parse result
        result = AgentExtractionResult(**data)
        print_success(f"Loaded extraction: {result.officer_bio.name if result.officer_bio else 'N/A'}")

        # Show basic info
        console.print("\n[bold cyan]Extraction Summary:[/bold cyan]")
        console.print(f"  Status: {'Success' if result.success else 'Failed'}")
        console.print(f"  Conversation Turns: {result.conversation_turns}")
        console.print(f"  Tool Calls: {len(result.tool_calls)}")
        console.print(f"  Total Tokens: {result.get_total_tokens():,}")

        # Show tool calls
        if result.tool_calls:
            console.print("\n[bold cyan]Tool Call Sequence:[/bold cyan]\n")

            tool_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
            tool_table.add_column("#", style="dim", width=4)
            tool_table.add_column("Tool", style="cyan", width=30)
            tool_table.add_column("Status", style="white", width=10)
            tool_table.add_column("Timestamp", style="dim", width=20)

            for i, tool in enumerate(result.tool_calls, 1):
                status = "[green]✓[/green]" if tool.success else "[red]✗[/red]"
                timestamp = tool.timestamp.strftime("%H:%M:%S") if hasattr(tool.timestamp, 'strftime') else str(tool.timestamp)
                tool_table.add_row(str(i), tool.tool_name, status, timestamp)

            console.print(tool_table)

        # Show extracted data
        if result.officer_bio:
            console.print("\n[bold cyan]Extracted Officer Bio:[/bold cyan]\n")

            # Display as formatted JSON
            bio_json = result.officer_bio.to_json(exclude_none=True, indent=2)
            syntax = Syntax(bio_json, "json", theme="monokai", line_numbers=False)
            console.print(syntax)

        # Show error if failed
        if not result.success:
            console.print("\n[bold red]Error Message:[/bold red]")
            console.print(f"  {result.error_message}")

        return 0

    except Exception as e:
        print_error(f"Replay failed: {e}")
        logger.exception("Replay error")
        return 1


# ============================================================================
# Command: stats
# ============================================================================

def cmd_stats(args):
    """
    Analyze all extractions in directory.

    Args:
        args: Parsed command-line arguments
    """
    print_header("Aggregate Statistics", f"Directory: {args.dir}")

    logger = logging.getLogger(__name__)

    try:
        # Find all extraction JSON files
        output_dir = Path(args.dir)
        if not output_dir.exists():
            print_error(f"Directory not found: {args.dir}")
            return 1

        json_files = list(output_dir.glob("*.json"))

        # Exclude review files and batch reports
        json_files = [
            f for f in json_files
            if not f.name.startswith("REVIEW_") and not f.name.startswith("batch_report")
        ]

        if not json_files:
            print_warning(f"No extraction files found in {args.dir}")
            return 1

        console.print(f"\n[cyan]Found {len(json_files)} extraction files[/cyan]")

        # Collect statistics
        results = []
        officers = []
        tools_used = []
        errors = []

        for json_file in track(json_files, description="Analyzing..."):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                result = AgentExtractionResult(**data)
                results.append(result)

                if result.officer_bio:
                    officers.append(result.officer_bio)

                for tool in result.tool_calls:
                    tools_used.append(tool.tool_name)

                if not result.success and result.error_message:
                    errors.append(result.error_message)

            except Exception as e:
                logger.debug(f"Skipping {json_file}: {e}")

        # Calculate statistics
        total_count = len(results)
        successful_count = sum(1 for r in results if r.success)
        failed_count = total_count - successful_count

        # Confidence scores
        confidence_scores = [o.confidence_score for o in officers]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

        # Token usage
        total_tokens = sum(r.get_total_tokens() for r in results)
        avg_tokens = total_tokens / total_count if total_count > 0 else 0

        # Tool usage
        tool_counter = Counter(tools_used)

        # Date completeness
        has_birth_date = sum(1 for o in officers if o.birth_date)
        has_death_date = sum(1 for o in officers if o.death_date)
        has_promotions = sum(1 for o in officers if o.promotions)

        # Display statistics
        console.print("\n[bold cyan]Overall Statistics:[/bold cyan]\n")

        overall_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
        overall_table.add_column("Metric", style="cyan", width=30)
        overall_table.add_column("Value", style="white", width=20)

        overall_table.add_row("Total Extractions", str(total_count))
        overall_table.add_row("Successful", f"{successful_count} ({successful_count/total_count*100:.1f}%)")
        overall_table.add_row("Failed", f"{failed_count} ({failed_count/total_count*100:.1f}%)")
        overall_table.add_row("", "")
        overall_table.add_row("Average Confidence", f"{avg_confidence:.3f}")
        overall_table.add_row("Min Confidence", f"{min(confidence_scores):.3f}" if confidence_scores else "N/A")
        overall_table.add_row("Max Confidence", f"{max(confidence_scores):.3f}" if confidence_scores else "N/A")
        overall_table.add_row("", "")
        overall_table.add_row("Total Tokens", f"{total_tokens:,}")
        overall_table.add_row("Avg Tokens/Extraction", f"{avg_tokens:,.0f}")

        console.print(overall_table)

        # Data completeness
        console.print("\n[bold cyan]Data Completeness:[/bold cyan]\n")

        completeness_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
        completeness_table.add_column("Field", style="cyan", width=30)
        completeness_table.add_column("Present", style="white", width=20)

        officer_count = len(officers)
        if officer_count > 0:
            completeness_table.add_row("Birth Date", f"{has_birth_date}/{officer_count} ({has_birth_date/officer_count*100:.1f}%)")
            completeness_table.add_row("Death Date", f"{has_death_date}/{officer_count} ({has_death_date/officer_count*100:.1f}%)")
            completeness_table.add_row("Promotions", f"{has_promotions}/{officer_count} ({has_promotions/officer_count*100:.1f}%)")

        console.print(completeness_table)

        # Tool usage
        console.print("\n[bold cyan]Tool Usage:[/bold cyan]\n")

        tool_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
        tool_table.add_column("Tool", style="cyan", width=35)
        tool_table.add_column("Count", style="white", width=15)

        for tool_name, count in tool_counter.most_common():
            tool_table.add_row(tool_name, str(count))

        console.print(tool_table)

        # Common errors
        if errors:
            console.print("\n[bold cyan]Common Errors:[/bold cyan]\n")
            error_counter = Counter(errors)

            error_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
            error_table.add_column("Error", style="red", width=60)
            error_table.add_column("Count", style="white", width=10)

            for error, count in error_counter.most_common(5):
                error_short = error[:57] + "..." if len(error) > 60 else error
                error_table.add_row(error_short, str(count))

            console.print(error_table)

        print_success(f"Analyzed {total_count} extractions")
        return 0

    except Exception as e:
        print_error(f"Stats analysis failed: {e}")
        logger.exception("Stats error")
        return 1


# ============================================================================
# Command: interactive
# ============================================================================

def cmd_interactive(args):
    """
    Interactive REPL-style interface.

    Args:
        args: Parsed command-line arguments
    """
    print_header("Interactive Mode", "REPL-style interface for quick testing")

    logger = logging.getLogger(__name__)

    # Initialize SDK once for session
    try:
        console.print("\n[cyan]Initializing SDK...[/cyan]")
        sdk = PLAgentSDK(require_db=False)
        print_success("SDK initialized - Ready for commands")
    except Exception as e:
        print_error(f"Failed to initialize SDK: {e}")
        return 1

    # Session statistics and history
    session_stats = {
        'extractions': 0,
        'successful': 0,
        'failed': 0,
        'total_tokens': 0
    }
    command_history = []
    last_result = None

    # Show welcome message
    console.print("\n[bold cyan]📋 Extraction Commands:[/bold cyan]")
    console.print("  [yellow]extract <url>[/yellow]     - Extract from URL")
    console.print("  [yellow]paste[/yellow]              - Paste source text")
    console.print("  [yellow]test[/yellow]               - Run test extraction")
    console.print("  [yellow]batch <file>[/yellow]       - Batch process URLs")
    console.print("\n[bold cyan]🔍 Analysis Commands:[/bold cyan]")
    console.print("  [yellow]validate <file>[/yellow]    - Validate saved extraction")
    console.print("  [yellow]replay <file>[/yellow]      - Replay conversation")
    console.print("  [yellow]search <query>[/yellow]     - Search output files")
    console.print("\n[bold cyan]🛠️  System Commands:[/bold cyan]")
    console.print("  [yellow]run-tests[/yellow]          - Run test suite")
    console.print("  [yellow]demo[/yellow]               - Run presentation demo")
    console.print("  [yellow]config[/yellow]             - Show configuration")
    console.print("  [yellow]stats[/yellow]              - Session statistics")
    console.print("  [yellow]api-check[/yellow]          - Check API connection")
    console.print("  [yellow]db-check[/yellow]           - Check database connection")
    console.print("\n[bold cyan]💡 Utility Commands:[/bold cyan]")
    console.print("  [yellow]history[/yellow]            - Show command history")
    console.print("  [yellow]clear[/yellow]              - Clear screen")
    console.print("  [yellow]help[/yellow]               - Show this help")
    console.print("  [yellow]exit[/yellow], [yellow]quit[/yellow], [yellow]q[/yellow]       - Exit interactive mode")
    console.print("\n[dim]Type command name for usage. Example: extract https://...[/dim]\n")

    # REPL loop
    while True:
        try:
            # Get command
            command = Prompt.ask("\n[bold cyan]plAgent>[/bold cyan]").strip()

            if not command:
                continue

            # Parse command
            parts = command.split(maxsplit=1)
            cmd = parts[0].lower()
            args_str = parts[1] if len(parts) > 1 else ""

            # Add to history
            command_history.append(command)

            # Handle commands
            if cmd in ['exit', 'quit', 'q']:
                console.print("\n[yellow]Exiting interactive mode...[/yellow]")
                break

            elif cmd == 'help':
                console.print("\n[bold cyan]Interactive Mode Commands:[/bold cyan]\n")

                # Extraction commands
                console.print("[bold magenta]📋 Extraction:[/bold magenta]")
                extract_table = Table(show_header=False, box=None, padding=(0, 2))
                extract_table.add_column("Command", style="yellow", width=20)
                extract_table.add_column("Description", style="white", width=50)
                extract_table.add_row("extract <url>", "Extract biography from URL")
                extract_table.add_row("paste", "Paste obituary text (multi-line)")
                extract_table.add_row("test", "Run test extraction on sample data")
                extract_table.add_row("batch <file>", "Batch process URLs from file")
                console.print(extract_table)

                # Analysis commands
                console.print("\n[bold magenta]🔍 Analysis:[/bold magenta]")
                analysis_table = Table(show_header=False, box=None, padding=(0, 2))
                analysis_table.add_column("Command", style="yellow", width=20)
                analysis_table.add_column("Description", style="white", width=50)
                analysis_table.add_row("validate <file>", "Re-validate saved extraction")
                analysis_table.add_row("replay <file>", "Replay conversation from file")
                analysis_table.add_row("search <query>", "Search output files by name")
                console.print(analysis_table)

                # System commands
                console.print("\n[bold magenta]🛠️  System:[/bold magenta]")
                system_table = Table(show_header=False, box=None, padding=(0, 2))
                system_table.add_column("Command", style="yellow", width=20)
                system_table.add_column("Description", style="white", width=50)
                system_table.add_row("run-tests", "Run comprehensive test suite")
                system_table.add_row("demo", "Run full presentation demo")
                system_table.add_row("config", "Show current configuration")
                system_table.add_row("stats", "Show session statistics")
                system_table.add_row("api-check", "Check Anthropic API connection")
                system_table.add_row("db-check", "Check database connection")
                console.print(system_table)

                # Utility commands
                console.print("\n[bold magenta]💡 Utility:[/bold magenta]")
                utility_table = Table(show_header=False, box=None, padding=(0, 2))
                utility_table.add_column("Command", style="yellow", width=20)
                utility_table.add_column("Description", style="white", width=50)
                utility_table.add_row("history", "Show command history")
                utility_table.add_row("clear", "Clear screen")
                utility_table.add_row("help", "Show this help")
                utility_table.add_row("exit, quit, q", "Exit interactive mode")
                console.print(utility_table)

                console.print("\n[dim]Examples:[/dim]")
                console.print("  [dim]extract https://www.news.cn/obituary.html[/dim]")
                console.print("  [dim]validate output/林炳尧_20260212.json[/dim]")
                console.print("  [dim]batch urls.txt[/dim]")
                console.print("  [dim]run-tests --fast[/dim]")

            elif cmd == 'extract':
                if not args_str:
                    print_error("Usage: extract <url>")
                    continue

                url = args_str.strip()

                console.print(f"\n[cyan]Extracting from URL...[/cyan]")

                try:
                    # Fetch source content
                    from fetch_source import fetch_source_content
                    with console.status("[cyan]Fetching content...[/cyan]", spinner="dots"):
                        source_text = fetch_source_content(url)

                    if not source_text:
                        print_error("Failed to fetch content")
                        continue

                    print_success(f"Fetched {len(source_text)} characters")
                    console.print("[dim]Claude will identify source type and adapt expectations[/dim]")

                    # Extract with universal profile
                    console.print("\n[cyan]Extracting biography (watch tool calls)...[/cyan]\n")

                    result = sdk.extract_bio_agentic(
                        source_text=source_text,
                        source_url=url,
                        source_type="universal"  # Universal extraction
                    )

                    # Update stats
                    session_stats['extractions'] += 1
                    if result.success:
                        session_stats['successful'] += 1
                    else:
                        session_stats['failed'] += 1
                    session_stats['total_tokens'] += result.get_total_tokens()

                    # Show results
                    if result.success and result.officer_bio:
                        officer = result.officer_bio

                        console.print("\n[bold green]✓ Extraction Successful![/bold green]\n")

                        # Quick summary
                        summary_table = Table(show_header=False, box=box.SIMPLE)
                        summary_table.add_column("Field", style="cyan", width=20)
                        summary_table.add_column("Value", style="white", width=50)

                        summary_table.add_row("Name", officer.name)
                        if officer.pinyin_name:
                            summary_table.add_row("Pinyin", officer.pinyin_name)
                        if officer.hometown:
                            summary_table.add_row("Hometown", officer.hometown)
                        summary_table.add_row("Confidence", f"{officer.confidence_score:.2f}")
                        summary_table.add_row("Tokens Used", f"{result.get_total_tokens():,}")
                        summary_table.add_row("Tool Calls", str(len(result.tool_calls)))

                        console.print(summary_table)

                        # Save result
                        output_file = sdk.save_result_to_file(result)
                        console.print(f"\n[dim]Saved to: {output_file}[/dim]")

                        # Suggest next actions
                        console.print("\n[bold cyan]Suggested Actions:[/bold cyan]")
                        if officer.confidence_score >= 0.8:
                            console.print("  [green]• High confidence - Ready for database[/green]")
                        else:
                            console.print("  [yellow]• Low confidence - Review recommended[/yellow]")
                        console.print(f"  [cyan]• Validate: python cli.py validate --json {output_file}[/cyan]")
                        console.print(f"  [cyan]• Replay: python cli.py replay --json {output_file}[/cyan]")

                    else:
                        print_error(f"Extraction failed: {result.error_message}")

                except Exception as e:
                    print_error(f"Extraction error: {e}")
                    logger.exception("Interactive extraction error")
                    session_stats['failed'] += 1

            elif cmd == 'paste':
                console.print("\n[cyan]Paste source text (press Ctrl+D or Ctrl+Z when done):[/cyan]")
                console.print("[dim]Tip: You can paste multiple lines[/dim]\n")

                try:
                    lines = []
                    while True:
                        try:
                            line = input()
                            lines.append(line)
                        except EOFError:
                            break

                    source_text = '\n'.join(lines)

                    if not source_text.strip():
                        print_warning("No text entered")
                        continue

                    print_success(f"Received {len(source_text)} characters")

                    # Extract
                    console.print("\n[cyan]Extracting biography...[/cyan]")
                    console.print("[dim]Claude will identify source type and adapt expectations[/dim]\n")

                    result = sdk.extract_bio_agentic(
                        source_text=source_text,
                        source_url="https://interactive/paste",
                        source_type="universal"  # Universal extraction
                    )

                    # Update stats
                    session_stats['extractions'] += 1
                    if result.success:
                        session_stats['successful'] += 1
                    else:
                        session_stats['failed'] += 1
                    session_stats['total_tokens'] += result.get_total_tokens()

                    # Show results (same as extract)
                    if result.success and result.officer_bio:
                        officer = result.officer_bio

                        console.print("\n[bold green]✓ Extraction Successful![/bold green]\n")

                        summary_table = Table(show_header=False, box=box.SIMPLE)
                        summary_table.add_column("Field", style="cyan", width=20)
                        summary_table.add_column("Value", style="white", width=50)

                        summary_table.add_row("Name", officer.name)
                        if officer.pinyin_name:
                            summary_table.add_row("Pinyin", officer.pinyin_name)
                        summary_table.add_row("Confidence", f"{officer.confidence_score:.2f}")
                        summary_table.add_row("Tokens Used", f"{result.get_total_tokens():,}")

                        console.print(summary_table)

                        output_file = sdk.save_result_to_file(result)
                        console.print(f"\n[dim]Saved to: {output_file}[/dim]")

                    else:
                        print_error(f"Extraction failed: {result.error_message}")

                except KeyboardInterrupt:
                    console.print("\n[yellow]Paste cancelled[/yellow]")

            elif cmd == 'test':
                console.print("\n[cyan]Running test extraction...[/cyan]")

                try:
                    test_file = Path("data/test_obituary.txt")
                    if not test_file.exists():
                        print_error("Test file not found: data/test_obituary.txt")
                        continue

                    source_text = extract_text_from_file(str(test_file))
                    print_success(f"Loaded {len(source_text)} characters")

                    console.print("[cyan]Extracting...[/cyan]")
                    console.print("[dim]Using universal extraction[/dim]\n")

                    result = sdk.extract_bio_agentic(
                        source_text=source_text,
                        source_url="https://interactive/test",
                        source_type="universal"
                    )

                    # Update stats
                    session_stats['extractions'] += 1
                    if result.success:
                        session_stats['successful'] += 1
                    else:
                        session_stats['failed'] += 1
                    session_stats['total_tokens'] += result.get_total_tokens()

                    # Show results
                    if result.success:
                        officer = result.officer_bio
                        print_success(f"Test passed: {officer.name}")
                        console.print(f"  Confidence: {officer.confidence_score:.2f}")
                        console.print(f"  Tokens: {result.get_total_tokens():,}")
                    else:
                        print_error(f"Test failed: {result.error_message}")

                except Exception as e:
                    print_error(f"Test error: {e}")
                    session_stats['failed'] += 1

            elif cmd == 'stats':
                console.print("\n[bold cyan]Session Statistics:[/bold cyan]\n")

                stats_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
                stats_table.add_column("Metric", style="cyan", width=30)
                stats_table.add_column("Value", style="white", width=20)

                stats_table.add_row("Total Extractions", str(session_stats['extractions']))
                stats_table.add_row("Successful", str(session_stats['successful']))
                stats_table.add_row("Failed", str(session_stats['failed']))

                if session_stats['extractions'] > 0:
                    success_rate = session_stats['successful'] / session_stats['extractions'] * 100
                    stats_table.add_row("Success Rate", f"{success_rate:.1f}%")

                stats_table.add_row("Total Tokens", f"{session_stats['total_tokens']:,}")

                if session_stats['extractions'] > 0:
                    avg_tokens = session_stats['total_tokens'] / session_stats['extractions']
                    stats_table.add_row("Avg Tokens/Extraction", f"{avg_tokens:,.0f}")

                console.print(stats_table)

            elif cmd == 'demo':
                console.print("\n[bold cyan]Starting Presentation Demo...[/bold cyan]")
                console.print("[dim]This will run the full team presentation (2-3 minutes)[/dim]")
                console.print("[yellow]Tip: Increase terminal font size for better visibility[/yellow]\n")

                try:
                    import subprocess
                    import sys

                    # Run demo.py in same Python environment
                    result = subprocess.run(
                        [sys.executable, "demo.py"],
                        cwd=Path(__file__).parent,
                        check=False
                    )

                    if result.returncode == 0:
                        console.print("\n[green]✓ Demo completed successfully[/green]")
                    else:
                        console.print(f"\n[yellow]Demo exited with code {result.returncode}[/yellow]")

                except FileNotFoundError:
                    print_error("demo.py not found in current directory")
                    console.print("[dim]Make sure you're in the pla-agent-sdk directory[/dim]")
                except KeyboardInterrupt:
                    console.print("\n[yellow]Demo interrupted by user[/yellow]")
                except Exception as e:
                    print_error(f"Demo error: {e}")

                console.print("\n[cyan]Press Enter to continue...[/cyan]")
                input()

            elif cmd == 'run-tests':
                console.print("\n[bold cyan]Running Test Suite...[/bold cyan]")

                # Parse optional flags
                test_args = args_str.split() if args_str else []

                try:
                    import subprocess
                    import sys

                    # Build command
                    test_cmd = [sys.executable, "run_all_tests.py"]
                    test_cmd.extend(test_args)

                    console.print(f"[dim]Command: {' '.join(test_cmd)}[/dim]\n")

                    # Run tests
                    result = subprocess.run(
                        test_cmd,
                        cwd=Path(__file__).parent,
                        check=False
                    )

                    console.print()
                    if result.returncode == 0:
                        console.print("[green]✓ All tests passed![/green]")
                        console.print("[dim]View detailed results: open test_results.html[/dim]")
                    else:
                        console.print("[yellow]⚠ Some tests failed[/yellow]")
                        console.print("[dim]Check test_results.html for details[/dim]")

                except FileNotFoundError:
                    print_error("run_all_tests.py not found")
                except KeyboardInterrupt:
                    console.print("\n[yellow]Tests interrupted[/yellow]")
                except Exception as e:
                    print_error(f"Test error: {e}")

                console.print("\n[cyan]Press Enter to continue...[/cyan]")
                input()

            elif cmd == 'validate':
                if not args_str:
                    print_error("Usage: validate <json_file>")
                    console.print("[dim]Example: validate output/林炳尧_20260212.json[/dim]")
                    continue

                json_file = Path(args_str.strip())

                if not json_file.exists():
                    print_error(f"File not found: {json_file}")
                    continue

                console.print(f"\n[cyan]Validating: {json_file.name}[/cyan]\n")

                try:
                    # Load extraction result
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    officer_data = data.get('officer_bio')
                    if not officer_data:
                        print_error("No officer_bio found in file")
                        continue

                    # Validate using schema
                    from schema import OfficerBio
                    officer = OfficerBio(**officer_data)

                    # Show validation results
                    console.print("[green]✓ Schema Validation: PASSED[/green]")
                    console.print(f"  Officer: {officer.name}")
                    console.print(f"  Confidence: {officer.confidence_score:.2f}")

                    # Check date logic
                    validation_checks = []

                    if officer.birth_date and officer.death_date:
                        birth_year = int(officer.birth_date[:4])
                        death_year = int(officer.death_date[:4])
                        if death_year > birth_year:
                            validation_checks.append(("Date Logic", "✓", "green"))
                        else:
                            validation_checks.append(("Date Logic", "✗", "red"))

                    if officer.promotions:
                        validation_checks.append((f"Promotions ({len(officer.promotions)})", "✓", "green"))

                    if officer.notable_positions:
                        validation_checks.append((f"Positions ({len(officer.notable_positions)})", "✓", "green"))

                    console.print()
                    for check_name, status, color in validation_checks:
                        console.print(f"  [{color}]{status}[/{color}] {check_name}")

                    console.print()
                    print_success("Validation complete")

                except json.JSONDecodeError:
                    print_error("Invalid JSON file")
                except Exception as e:
                    print_error(f"Validation failed: {e}")

            elif cmd == 'replay':
                if not args_str:
                    print_error("Usage: replay <json_file>")
                    console.print("[dim]Example: replay output/林炳尧_20260212.json[/dim]")
                    continue

                json_file = Path(args_str.strip())

                if not json_file.exists():
                    print_error(f"File not found: {json_file}")
                    continue

                console.print(f"\n[cyan]Replaying: {json_file.name}[/cyan]\n")

                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Show summary
                    console.print("[bold]Extraction Summary:[/bold]")
                    console.print(f"  Success: {'✓' if data.get('success') else '✗'}")
                    console.print(f"  Turns: {data.get('conversation_turns', 0)}")
                    console.print(f"  Tool Calls: {len(data.get('tool_calls', []))}")
                    console.print(f"  Tokens: {data.get('total_input_tokens', 0) + data.get('total_output_tokens', 0):,}")
                    console.print()

                    # Show tool calls
                    if data.get('tool_calls'):
                        console.print("[bold cyan]Tool Call Sequence:[/bold cyan]\n")

                        for idx, tc in enumerate(data['tool_calls'], 1):
                            status = "✓" if tc.get('success') else "✗"
                            color = "green" if tc.get('success') else "red"
                            console.print(f"  [{color}]{status}[/{color}] {idx}. {tc.get('tool_name')}")

                    # Show officer bio
                    if data.get('officer_bio'):
                        console.print()
                        console.print("[bold cyan]Extracted Officer Bio:[/bold cyan]\n")
                        officer_preview = json.dumps(data['officer_bio'], indent=2, ensure_ascii=False)
                        console.print(officer_preview[:500] + "..." if len(officer_preview) > 500 else officer_preview)

                except json.JSONDecodeError:
                    print_error("Invalid JSON file")
                except Exception as e:
                    print_error(f"Replay error: {e}")

            elif cmd == 'batch':
                if not args_str:
                    print_error("Usage: batch <url_file>")
                    console.print("[dim]Example: batch urls.txt[/dim]")
                    continue

                url_file = Path(args_str.strip())

                if not url_file.exists():
                    print_error(f"File not found: {url_file}")
                    continue

                console.print(f"\n[bold cyan]Starting Batch Processing...[/bold cyan]")
                console.print(f"[dim]File: {url_file}[/dim]")
                console.print("[yellow]Note: This will use API credits[/yellow]\n")

                # Ask for confirmation
                confirm = Prompt.ask("Continue? [y/N]", default="n")
                if confirm.lower() != 'y':
                    console.print("[yellow]Batch processing cancelled[/yellow]")
                    continue

                try:
                    from batch_processor import BatchProcessor

                    processor = BatchProcessor(require_db=False)
                    results = processor.process_file(str(url_file))

                    # Update session stats
                    for result in results:
                        session_stats['extractions'] += 1
                        if result.success:
                            session_stats['successful'] += 1
                        else:
                            session_stats['failed'] += 1
                        session_stats['total_tokens'] += result.get_total_tokens()

                    console.print()
                    print_success(f"Batch complete: {len(results)} processed")

                except FileNotFoundError as e:
                    print_error(f"Import error: {e}")
                except KeyboardInterrupt:
                    console.print("\n[yellow]Batch processing interrupted[/yellow]")
                except Exception as e:
                    print_error(f"Batch error: {e}")

            elif cmd == 'config':
                console.print("\n[bold cyan]Current Configuration:[/bold cyan]\n")

                from config import CONFIG

                config_table = Table(show_header=False, box=box.SIMPLE)
                config_table.add_column("Setting", style="cyan", width=30)
                config_table.add_column("Value", style="white", width=50)

                # API settings
                api_key = CONFIG.ANTHROPIC_API_KEY
                api_display = f"{api_key[:12]}...{api_key[-4:]}" if api_key else "[red]Not set[/red]"
                config_table.add_row("ANTHROPIC_API_KEY", api_display)
                config_table.add_row("MODEL_NAME", CONFIG.MODEL_NAME)
                config_table.add_row("MAX_ITERATIONS", str(CONFIG.MAX_ITERATIONS))

                # Database settings
                if CONFIG.DATABASE_URL:
                    db_display = f"{CONFIG.DATABASE_URL[:20]}..."
                    config_table.add_row("DATABASE_URL", db_display)
                elif CONFIG.DB_USER:
                    config_table.add_row("DB_HOST", CONFIG.DB_HOST)
                    config_table.add_row("DB_NAME", CONFIG.DB_NAME)
                    config_table.add_row("DB_USER", CONFIG.DB_USER)
                    config_table.add_row("DB_PASSWORD", "[dim]***[/dim]")
                else:
                    config_table.add_row("DATABASE", "[yellow]Not configured[/yellow]")

                console.print(config_table)

            elif cmd == 'api-check':
                console.print("\n[cyan]Checking Anthropic API connection...[/cyan]\n")

                try:
                    from anthropic import Anthropic
                    from config import CONFIG

                    with console.status("[cyan]Testing API...[/cyan]", spinner="dots"):
                        client = Anthropic(api_key=CONFIG.ANTHROPIC_API_KEY)

                        # Simple test call
                        response = client.messages.create(
                            model=CONFIG.MODEL_NAME,
                            max_tokens=10,
                            messages=[{"role": "user", "content": "Hi"}]
                        )

                    console.print("[green]✓ API Connection: SUCCESS[/green]")
                    console.print(f"  Model: {CONFIG.MODEL_NAME}")
                    console.print(f"  Response: {response.content[0].text if response.content else 'No text'}")

                except Exception as e:
                    console.print(f"[red]✗ API Connection: FAILED[/red]")
                    console.print(f"  Error: {str(e)[:100]}")

            elif cmd == 'db-check':
                console.print("\n[cyan]Checking database connection...[/cyan]\n")

                try:
                    from config import CONFIG
                    import psycopg2

                    if not CONFIG.DB_USER and not CONFIG.DATABASE_URL:
                        console.print("[yellow]⚠ Database not configured[/yellow]")
                        console.print("[dim]Add DATABASE_URL to .env to enable database features[/dim]")
                        continue

                    with console.status("[cyan]Testing connection...[/cyan]", spinner="dots"):
                        conn_str = CONFIG.get_db_connection_string()
                        conn = psycopg2.connect(conn_str)
                        cursor = conn.cursor()
                        cursor.execute("SELECT version();")
                        version = cursor.fetchone()[0]
                        conn.close()

                    console.print("[green]✓ Database Connection: SUCCESS[/green]")
                    console.print(f"  PostgreSQL: {version[:50]}")

                except ImportError:
                    console.print("[red]✗ psycopg2 not installed[/red]")
                    console.print("[dim]Run: pip install psycopg2-binary[/dim]")
                except Exception as e:
                    console.print(f"[red]✗ Database Connection: FAILED[/red]")
                    console.print(f"  Error: {str(e)[:100]}")

            elif cmd == 'search':
                if not args_str:
                    print_error("Usage: search <query>")
                    console.print("[dim]Example: search 林炳尧[/dim]")
                    continue

                query = args_str.strip()
                console.print(f"\n[cyan]Searching for: {query}[/cyan]\n")

                try:
                    output_dir = Path("output")
                    if not output_dir.exists():
                        console.print("[yellow]No output directory found[/yellow]")
                        continue

                    # Search JSON files
                    matches = []
                    for json_file in output_dir.glob("**/*.json"):
                        try:
                            with open(json_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if query.lower() in content.lower():
                                    matches.append(json_file)
                        except:
                            pass

                    if matches:
                        console.print(f"[green]Found {len(matches)} match(es):[/green]\n")
                        for match in matches[:10]:
                            console.print(f"  • {match.relative_to(output_dir)}")
                        if len(matches) > 10:
                            console.print(f"  [dim]... and {len(matches) - 10} more[/dim]")
                    else:
                        console.print("[yellow]No matches found[/yellow]")

                except Exception as e:
                    print_error(f"Search error: {e}")

            elif cmd == 'history':
                console.print("\n[bold cyan]Command History:[/bold cyan]\n")

                if not command_history:
                    console.print("[dim]No commands in history yet[/dim]")
                else:
                    for idx, hist_cmd in enumerate(command_history[-20:], 1):
                        console.print(f"  {idx}. {hist_cmd}")

                    if len(command_history) > 20:
                        console.print(f"\n[dim]Showing last 20 of {len(command_history)} commands[/dim]")

            elif cmd == 'clear':
                console.clear()

            else:
                print_error(f"Unknown command: {cmd}")
                console.print("[dim]Type 'help' for available commands[/dim]")

        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'exit' to quit[/yellow]")
            continue
        except EOFError:
            console.print("\n[yellow]Exiting...[/yellow]")
            break
        except Exception as e:
            print_error(f"Error: {e}")
            logger.exception("Interactive mode error")

    # Show final session stats
    if session_stats['extractions'] > 0:
        console.print("\n[bold cyan]Session Summary:[/bold cyan]")
        console.print(f"  Extractions: {session_stats['extractions']}")
        console.print(f"  Successful: {session_stats['successful']}")
        console.print(f"  Total Tokens: {session_stats['total_tokens']:,}")

    console.print("\n[green]Goodbye![/green]\n")
    return 0


# ============================================================================
# Main CLI
# ============================================================================

def create_parser():
    """Create argument parser with all commands."""
    parser = argparse.ArgumentParser(
        prog='pla-cli',
        description='PLA Agent SDK - Command Line Interface',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract from any URL (Claude identifies source type automatically)
  %(prog)s extract --url https://www.news.cn/obituary.html
  %(prog)s extract --url https://zh.wikipedia.org/wiki/Officer
  %(prog)s extract --url https://weibo.com/status/...

  # Extract with database saving
  %(prog)s extract --url https://www.news.cn/obituary.html --save-db

  # Batch process URLs from file (works with mixed source types)
  %(prog)s batch --file urls.txt

  # Run test suite
  %(prog)s test

  # Validate saved extraction
  %(prog)s validate --json output/林炳尧_20260211.json

  # Replay conversation
  %(prog)s replay --json output/林炳尧_20260211.json

  # Show statistics
  %(prog)s stats --dir output/

  # Interactive mode (REPL)
  %(prog)s interactive

For more information: https://github.com/your-org/pla-agent-sdk
        """
    )

    # Global arguments
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Show debug logs'
    )
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Command: extract
    parser_extract = subparsers.add_parser(
        'extract',
        help='Extract biography from single URL',
        description='Extract PLA officer biography from a single source URL'
    )
    parser_extract.add_argument(
        '--url',
        type=str,
        required=True,
        help='Source URL to extract from'
    )
    parser_extract.add_argument(
        '--save-db',
        action='store_true',
        help='Save to database if confidence meets threshold'
    )
    parser_extract.set_defaults(func=cmd_extract)

    # Command: batch
    parser_batch = subparsers.add_parser(
        'batch',
        help='Process multiple URLs from file',
        description='Batch process multiple source URLs from a text file'
    )
    parser_batch.add_argument(
        '--file', '-f',
        type=str,
        required=True,
        help='File containing URLs (one per line)'
    )
    parser_batch.add_argument(
        '--save-db',
        action='store_true',
        help='Save high-confidence results to database'
    )
    parser_batch.add_argument(
        '--parallel', '-p',
        type=int,
        metavar='N',
        help='Number of parallel workers (not yet implemented)'
    )
    parser_batch.add_argument(
        '--rate-limit',
        type=float,
        default=1.0,
        help='Seconds between requests (default: 1.0)'
    )
    parser_batch.set_defaults(func=cmd_batch)

    # Command: test
    parser_test = subparsers.add_parser(
        'test',
        help='Run test suite',
        description='Run extraction test suite on source file'
    )
    parser_test.add_argument(
        '--obituary',
        type=str,
        help='Test obituary file (default: data/test_obituary.txt)'
    )
    parser_test.set_defaults(func=cmd_test)

    # Command: validate
    parser_validate = subparsers.add_parser(
        'validate',
        help='Re-run validation on saved extraction',
        description='Re-run validation checks on a saved extraction JSON file'
    )
    parser_validate.add_argument(
        '--json',
        type=str,
        required=True,
        help='Path to saved extraction JSON file'
    )
    parser_validate.set_defaults(func=cmd_validate)

    # Command: replay
    parser_replay = subparsers.add_parser(
        'replay',
        help='Replay saved extraction conversation',
        description='Replay and display a saved extraction conversation'
    )
    parser_replay.add_argument(
        '--json',
        type=str,
        required=True,
        help='Path to saved extraction JSON file'
    )
    parser_replay.set_defaults(func=cmd_replay)

    # Command: stats
    parser_stats = subparsers.add_parser(
        'stats',
        help='Analyze all extractions in directory',
        description='Analyze and display aggregate statistics for all extractions'
    )
    parser_stats.add_argument(
        '--dir',
        type=str,
        default='output/',
        help='Directory containing extraction files (default: output/)'
    )
    parser_stats.set_defaults(func=cmd_stats)

    # Command: interactive
    parser_interactive = subparsers.add_parser(
        'interactive',
        help='Interactive REPL mode',
        description='Interactive REPL-style interface for quick testing and exploration'
    )
    parser_interactive.set_defaults(func=cmd_interactive)

    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Set up logging
    setup_logging(verbose=args.verbose, debug=args.debug)

    # Show help if no command
    if not args.command:
        parser.print_help()
        return 0

    # Execute command
    try:
        return args.func(args)
    except Exception as e:
        print_error(f"Command failed: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
