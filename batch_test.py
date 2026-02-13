#!/usr/bin/env python3
"""
Test script for BatchProcessor with data/test_urls.txt

Tests batch processing functionality including:
- URL processing from file
- Automatic review flagging
- Batch report generation
- Optional database saving
"""
import sys
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
import logging

from batch_processor import BatchProcessor
from tools.extraction_tools import extract_text_from_file

console = Console()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_mock_urls_if_needed():
    """
    Create mock URL file if using test obituary.

    Since we can't actually fetch from placeholder URLs,
    we'll process the local test_obituary.txt file instead.
    """
    test_obituary = Path("data/test_obituary.txt")

    if not test_obituary.exists():
        console.print("[yellow]⚠ Warning: data/test_obituary.txt not found[/yellow]")
        console.print("[yellow]  Please add a test obituary file or use real URLs[/yellow]")
        return False

    console.print(f"[cyan]Using local test obituary: {test_obituary}[/cyan]")
    return True


def process_with_local_files(processor, save_to_db=False):
    """
    Alternative processing method using local test file.

    This is used when URLs can't be fetched (placeholder URLs).
    Processes the local test_obituary.txt file multiple times to simulate batch processing.

    Args:
        processor: BatchProcessor instance
        save_to_db: Whether to save to database

    Returns:
        List of extraction results
    """
    console.print("\n[bold cyan]Processing local test obituary (simulating batch)...[/bold cyan]")

    test_file = Path("data/test_obituary.txt")
    if not test_file.exists():
        console.print(f"[red]✗ Test file not found: {test_file}[/red]")
        return []

    # Load test source text
    source_text = extract_text_from_file(str(test_file))
    console.print(f"[green]✓ Loaded test obituary ({len(source_text)} characters)[/green]")

    # Process 3 times to simulate batch (with slight variations in URLs)
    urls = [
        "https://www.news.cn/test/obituary_1.html",
        "https://www.news.cn/test/obituary_2.html",
        "https://www.news.cn/test/obituary_3.html",
    ]

    results = []

    console.print(f"\n[bold cyan]Processing {len(urls)} test extractions...[/bold cyan]\n")

    from tqdm import tqdm
    import time

    for i, url in enumerate(tqdm(urls, desc="Processing", unit="extraction")):
        try:
            # Apply rate limiting
            if i > 0:
                time.sleep(processor.rate_limit_seconds)

            # Extract using SDK
            logger.info(f"Extracting biography {i+1}/{len(urls)}")
            result = processor.sdk.extract_bio_agentic(
                source_text=source_text,
                source_url=url,
                source_type="universal"
            )

            # Update counters
            processor.total_processed += 1
            if result.success:
                processor.total_successful += 1
            else:
                processor.total_failed += 1

            # Save result to file
            processor._save_result_to_file(result, url)

            # Check confidence and flag for review if needed
            if result.success and result.officer_bio:
                confidence = result.officer_bio.confidence_score

                if confidence < 0.7:
                    processor.flag_for_review(
                        result,
                        url,
                        f"Low confidence score: {confidence:.2f}"
                    )
                elif save_to_db:
                    # High confidence - save to database if requested
                    try:
                        from tools.database_tools import save_officer_bio_to_database
                        db_result = save_officer_bio_to_database(result.officer_bio)
                        if db_result:
                            logger.info(f"✓ Saved to database: {result.officer_bio.name}")
                        else:
                            logger.warning(f"⚠ Database save failed for: {result.officer_bio.name}")
                    except Exception as e:
                        logger.error(f"Database error: {e}")
            else:
                processor.flag_for_review(
                    result,
                    url,
                    f"Extraction failed: {result.error_message}"
                )

            results.append(result)

        except Exception as e:
            logger.error(f"Error processing {url}: {e}", exc_info=True)
            processor.total_failed += 1

    console.print(f"\n[bold green]✓ Completed {len(results)} extractions[/bold green]\n")
    return results


def print_detailed_summary(processor, results):
    """
    Print detailed summary of batch processing results.

    Args:
        processor: BatchProcessor instance
        results: List of AgentExtractionResult
    """
    console.print("\n" + "=" * 80)
    console.print(Panel.fit(
        "[bold magenta]Batch Test Summary[/bold magenta]",
        border_style="magenta"
    ))

    # Overall statistics
    total = len(results)
    successful = sum(1 for r in results if r.success)
    failed = total - successful

    summary_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
    summary_table.add_column("Metric", style="cyan", width=30)
    summary_table.add_column("Value", style="white", width=20)

    summary_table.add_row("Total Processed", str(processor.total_processed))
    summary_table.add_row("Successful", f"{successful} ({successful/total*100:.1f}%)" if total > 0 else "0")
    summary_table.add_row("Failed", str(failed))
    summary_table.add_row("Flagged for Review", str(processor.total_flagged_for_review))

    console.print("\n", summary_table)

    # Individual results
    if results:
        console.print("\n[bold cyan]Individual Results:[/bold cyan]\n")

        results_table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        results_table.add_column("#", style="dim", width=3)
        results_table.add_column("Officer Name", style="cyan", width=20)
        results_table.add_column("Confidence", style="white", width=12)
        results_table.add_column("Tokens", style="dim", width=10)
        results_table.add_column("Tools", style="dim", width=7)
        results_table.add_column("Status", style="white", width=15)

        for i, result in enumerate(results, 1):
            if result.success and result.officer_bio:
                officer = result.officer_bio
                name = officer.name
                confidence = f"{officer.confidence_score:.2f}"
                tokens = f"{result.get_total_tokens():,}"
                tool_count = str(len(result.tool_calls))

                # Determine status
                if officer.confidence_score >= 0.7:
                    status = "[green]✓ Good[/green]"
                else:
                    status = "[yellow]⚠ Review[/yellow]"
            else:
                name = "N/A"
                confidence = "N/A"
                tokens = f"{result.get_total_tokens():,}" if hasattr(result, 'total_input_tokens') else "N/A"
                tool_count = str(len(result.tool_calls)) if hasattr(result, 'tool_calls') else "N/A"
                status = "[red]✗ Failed[/red]"

            results_table.add_row(str(i), name, confidence, tokens, tool_count, status)

        console.print(results_table)

    # Items needing review
    if processor.total_flagged_for_review > 0:
        console.print("\n[bold yellow]⚠ Items Needing Human Review:[/bold yellow]")
        console.print(f"[yellow]Check {processor.review_dir} for flagged extractions[/yellow]")

        # List flagged files
        review_files = list(processor.review_dir.glob("REVIEW_*.json"))
        if review_files:
            console.print(f"\n[yellow]Flagged files ({len(review_files)}):[/yellow]")
            for rf in review_files[-5:]:  # Show last 5
                console.print(f"  [dim]• {rf.name}[/dim]")
            if len(review_files) > 5:
                console.print(f"  [dim]... and {len(review_files) - 5} more[/dim]")

    # Cost estimation
    if results:
        total_tokens = sum(r.get_total_tokens() for r in results)
        # Sonnet 4.5 pricing: $3/M input, $15/M output
        total_input = sum(r.total_input_tokens for r in results)
        total_output = sum(r.total_output_tokens for r in results)
        estimated_cost = (total_input / 1_000_000 * 3) + (total_output / 1_000_000 * 15)

        console.print(f"\n[bold cyan]Cost Estimation:[/bold cyan]")
        console.print(f"  Total tokens: {total_tokens:,}")
        console.print(f"  Estimated cost: ${estimated_cost:.4f}")
        console.print(f"  Average cost per extraction: ${estimated_cost/total:.4f}")

    console.print("\n" + "=" * 80 + "\n")


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(
        description="Test batch processing with data/test_urls.txt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic test
  python batch_test.py

  # Test with database saving
  python batch_test.py --save-db

  # Use real URLs (if available)
  python batch_test.py --use-real-urls
        """
    )

    parser.add_argument(
        '--save-db',
        action='store_true',
        help='Save high-confidence results to database'
    )
    parser.add_argument(
        '--use-real-urls',
        action='store_true',
        help='Try to fetch from URLs (default: use local test file)'
    )
    parser.add_argument(
        '--rate-limit',
        type=float,
        default=1.0,
        help='Seconds between requests (default: 1.0)'
    )

    args = parser.parse_args()

    # Print header
    console.print("\n" + "=" * 80)
    console.print(Panel.fit(
        "[bold magenta]Batch Processor Test Script[/bold magenta]\n"
        "Testing batch processing with data/test_urls.txt",
        border_style="magenta"
    ))
    console.print("=" * 80 + "\n")

    # Check for test obituary
    if not args.use_real_urls:
        if not create_mock_urls_if_needed():
            console.print("[red]✗ Cannot proceed without test obituary[/red]")
            return 1

    # Initialize processor
    console.print("[cyan]Initializing BatchProcessor...[/cyan]")
    try:
        processor = BatchProcessor(
            require_db=args.save_db,
            rate_limit_seconds=args.rate_limit
        )
        console.print("[green]✓ BatchProcessor initialized[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed to initialize BatchProcessor: {e}[/red]")
        return 1

    # Process URLs
    try:
        if args.use_real_urls:
            # Try to fetch from URLs
            console.print("[cyan]Processing from data/test_urls.txt (fetching from URLs)...[/cyan]")
            results = processor.process_from_file(
                "data/test_urls.txt",
                save_to_db=args.save_db
            )
        else:
            # Use local test file
            console.print("[cyan]Processing using local test obituary...[/cyan]")
            results = process_with_local_files(processor, save_to_db=args.save_db)

        if not results:
            console.print("[yellow]⚠ No results to process[/yellow]")
            return 1

        # Generate batch report
        console.print("\n[bold cyan]Generating batch report...[/bold cyan]")
        processor.generate_batch_report(results)

        # Print detailed summary
        print_detailed_summary(processor, results)

        # Success message
        console.print("[bold green]✓ Batch test completed successfully![/bold green]\n")

        # Next steps
        console.print(Panel(
            "[bold cyan]Next Steps:[/bold cyan]\n\n"
            "1. Check output/ directory for extraction results\n"
            "2. Review output/needs_review/ for flagged items\n"
            "3. Read output/batch_report_*.txt for detailed statistics\n"
            "4. Check batch_processing.log for detailed logs",
            title="📋 What's Next?",
            border_style="cyan"
        ))

        return 0

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Test interrupted by user[/yellow]")
        return 1
    except Exception as e:
        console.print(f"\n[red]✗ Test failed: {e}[/red]")
        logger.error(f"Batch test failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
