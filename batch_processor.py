#!/usr/bin/env python3
"""Batch processor for extracting PLA officer biographies from multiple obituaries."""
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from threading import Lock
from collections import Counter
import json

try:
    from tqdm import tqdm
except ImportError:
    class _NoopTqdm:
        def __init__(self, total=None, desc="", unit=""):
            self.total = total
            self.desc = desc
            self.unit = unit

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def set_description(self, _desc):
            return None

        def update(self, _n=1):
            return None

    def tqdm(*args, **kwargs):
        return _NoopTqdm(*args, **kwargs)
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from agent import PLAgentSDK
from schema import AgentExtractionResult
from fetch_source import fetch_source_content
from source_profiles import SourceProfileRegistry
from tools.database_tools import save_officer_bio_to_database
from safeguards import validate_source_text_not_fixture

logger = logging.getLogger(__name__)
console = Console()


class BatchProcessor:
    """Batch processor for extracting officer biographies from multiple obituaries."""

    def __init__(
        self,
        require_db: bool = False,
        rate_limit_seconds: float = 1.0
    ):
        """
        Initialize batch processor.

        Args:
            require_db: Whether database connection is required
            rate_limit_seconds: Seconds to wait between API requests (default: 1.0)
        """
        logger.info("Initializing BatchProcessor...")

        # Initialize SDK
        try:
            self.sdk = PLAgentSDK(require_db=require_db)
            logger.info("✓ PLAgentSDK initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PLAgentSDK: {e}")
            raise

        # Rate limiting configuration
        self.rate_limit_seconds = rate_limit_seconds
        self.last_request_time = 0
        self.request_lock = Lock()

        # Progress tracking
        self.total_processed = 0
        self.total_successful = 0
        self.total_failed = 0
        self.total_flagged_for_review = 0

        # Output directories
        self.output_dir = Path("output")
        self.review_dir = self.output_dir / "needs_review"
        self.output_dir.mkdir(exist_ok=True)
        self.review_dir.mkdir(exist_ok=True)

        logger.info(f"Rate limit: {rate_limit_seconds}s between requests")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"Review directory: {self.review_dir}")

    def _rate_limit(self):
        """Apply rate limiting to avoid API overload."""
        with self.request_lock:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.rate_limit_seconds:
                sleep_time = self.rate_limit_seconds - elapsed
                logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
            self.last_request_time = time.time()

    def _fetch_source(self, url: str) -> Optional[str]:
        """
        Fetch source text from URL.

        Args:
            url: URL of the source

        Returns:
            Extracted text content, or None if fetch failed
        """
        try:
            return fetch_source_content(url)
        except Exception as e:
            logger.error(f"Error fetching source from {url}: {e}")
            return None

    def _save_result_to_file(self, result: AgentExtractionResult, url: str) -> Optional[Path]:
        """
        Save extraction result to JSON file.

        Args:
            result: Extraction result to save
            url: Source URL

        Returns:
            Path to saved file, or None if save failed
        """
        try:
            if result.officer_bio:
                officer_name = result.officer_bio.name
            else:
                officer_name = "unknown"

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{officer_name}_{timestamp}.json"
            filepath = self.output_dir / filename

            # Create output dictionary
            output_data = result.to_dict(exclude_none=False)
            output_data['source_url'] = url

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            logger.info(f"✓ Saved result to: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Failed to save result to file: {e}")
            return None

    def flag_for_review(self, result: AgentExtractionResult, url: str, reason: str):
        """
        Flag result for human review.

        Args:
            result: Extraction result to flag
            url: Source URL
            reason: Reason for flagging
        """
        try:
            if result.officer_bio:
                officer_name = result.officer_bio.name
            else:
                officer_name = "unknown"

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"REVIEW_{officer_name}_{timestamp}.json"
            filepath = self.review_dir / filename

            # Create review data
            review_data = result.to_dict(exclude_none=False)
            review_data['source_url'] = url
            review_data['review_reason'] = reason
            review_data['flagged_at'] = datetime.now().isoformat()

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(review_data, f, ensure_ascii=False, indent=2)

            logger.warning(f"⚠ Flagged for review: {filepath} (Reason: {reason})")
            self.total_flagged_for_review += 1

        except Exception as e:
            logger.error(f"Failed to flag result for review: {e}")

    def process_urls(self, urls: List[str], save_to_db: bool = False) -> List[AgentExtractionResult]:
        """
        Process multiple URLs and extract officer biographies.

        Args:
            urls: List of source URLs to process
            save_to_db: Whether to save high-confidence results to database
        Returns:
            List of extraction results
        """
        results = []
        profile_registry = SourceProfileRegistry()
        profile = profile_registry.get("universal")
        review_threshold = profile.min_confidence_threshold

        console.print(f"\n[bold cyan]Processing {len(urls)} sources...[/bold cyan]\n")

        # Process each URL with progress bar
        with tqdm(total=len(urls), desc="Processing sources", unit="source") as pbar:
            for i, url in enumerate(urls):
                pbar.set_description(f"Processing {i+1}/{len(urls)}")

                try:
                    self.total_processed += 1

                    # Apply rate limiting
                    if i > 0:  # Skip rate limit for first request
                        self._rate_limit()

                    # Fetch source text
                    source_text = self._fetch_source(url)
                    if not source_text:
                        logger.error(f"Failed to fetch source from {url}")
                        self.total_failed += 1

                        results.append(AgentExtractionResult(
                            officer_bio=None,
                            success=False,
                            error_message="Failed to fetch source content"
                        ))
                        continue

                    # Extract biography using agent
                    validate_source_text_not_fixture(source_text, url, Path(__file__).parent)
                    logger.info(f"Extracting biography for URL {i+1}/{len(urls)}")
                    result = self.sdk.extract_bio_agentic(
                        source_text=source_text,
                        source_url=url
                    )

                    # Update counters
                    if result.success:
                        self.total_successful += 1
                    else:
                        self.total_failed += 1

                    # Save result to file
                    self._save_result_to_file(result, url)

                    # Check confidence and flag for review if needed
                    if result.success and result.officer_bio:
                        confidence = result.officer_bio.confidence_score

                        if confidence < review_threshold:
                            # Low confidence - flag for review
                            self.flag_for_review(
                                result,
                                url,
                                f"Low confidence score: {confidence:.2f} (threshold: {review_threshold:.2f})"
                            )
                        elif save_to_db:
                            # High confidence - save to database if requested
                            try:
                                db_result = save_officer_bio_to_database(result.officer_bio)
                                if db_result:
                                    logger.info(f"✓ Saved to database: {result.officer_bio.name}")
                                else:
                                    logger.warning(f"⚠ Database save failed for: {result.officer_bio.name}")
                            except Exception as e:
                                logger.error(f"Database error for {result.officer_bio.name}: {e}")
                    else:
                        # Extraction failed - flag for review
                        self.flag_for_review(
                            result,
                            url,
                            f"Extraction failed: {result.error_message}"
                        )

                    results.append(result)

                except KeyboardInterrupt:
                    logger.warning("Processing interrupted by user")
                    console.print("\n[yellow]⚠ Processing interrupted by user[/yellow]")
                    break

                except Exception as e:
                    logger.error(f"Unexpected error processing {url}: {e}", exc_info=True)
                    self.total_failed += 1
                    results.append(AgentExtractionResult(
                        officer_bio=None,
                        success=False,
                        error_message=f"Unexpected processing error: {e}"
                    ))

                finally:
                    pbar.update(1)

        console.print(f"\n[bold green]✓ Completed processing {self.total_processed} sources[/bold green]\n")
        return results

    def process_from_file(self, filepath: str, save_to_db: bool = False) -> List[AgentExtractionResult]:
        """
        Process URLs from a text file (one URL per line).

        Args:
            filepath: Path to file containing URLs
            save_to_db: Whether to save high-confidence results to database
        Returns:
            List of extraction results
        """
        logger.info(f"Reading URLs from file: {filepath}")

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

            logger.info(f"Found {len(urls)} URLs in file")
            console.print(f"[cyan]Found {len(urls)} URLs in {filepath}[/cyan]")

            return self.process_urls(urls, save_to_db=save_to_db)

        except FileNotFoundError:
            logger.error(f"File not found: {filepath}")
            console.print(f"[red]✗ File not found: {filepath}[/red]")
            return []
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            console.print(f"[red]✗ Error reading file: {e}[/red]")
            return []

    def generate_batch_report(self, results: List[AgentExtractionResult]):
        """
        Generate comprehensive batch processing report.

        Args:
            results: List of extraction results to analyze
        """
        if not results:
            console.print("[yellow]No results to generate report[/yellow]")
            return

        logger.info("Generating batch report...")

        # Calculate statistics
        total_count = len(results)
        successful_count = sum(1 for r in results if r.success)
        failed_count = total_count - successful_count
        overall_success_rate = (successful_count / total_count * 100) if total_count > 0 else 0

        # Confidence scores (only for successful extractions)
        confidence_scores = [r.officer_bio.confidence_score for r in results if r.success and r.officer_bio]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

        # Token usage
        total_input_tokens = sum(r.total_input_tokens for r in results)
        total_output_tokens = sum(r.total_output_tokens for r in results)
        total_tokens = sum(r.get_total_tokens() for r in results)
        avg_tokens = total_tokens / total_count if total_count > 0 else 0

        # Tool usage
        total_tool_calls = sum(len(r.tool_calls) for r in results)
        avg_tool_calls = total_tool_calls / total_count if total_count > 0 else 0

        # Conversation turns
        total_turns = sum(r.conversation_turns for r in results)
        avg_turns = total_turns / total_count if total_count > 0 else 0

        # Failure patterns
        error_messages = [r.error_message for r in results if not r.success and r.error_message]
        error_counter = Counter(error_messages)
        common_errors = error_counter.most_common(5)

        # Tool success rates
        all_tools = [tool.tool_name for r in results for tool in r.tool_calls]
        tool_counter = Counter(all_tools)
        tool_successes = Counter([tool.tool_name for r in results for tool in r.tool_calls if tool.success])

        # Generate report text
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.output_dir / f"batch_report_{timestamp}.txt"

        report_lines = [
            "=" * 80,
            "PLA AGENT SDK - BATCH PROCESSING REPORT",
            "=" * 80,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "=" * 80,
            "SUMMARY STATISTICS",
            "=" * 80,
            f"Total Processed:           {total_count}",
            f"Successful Extractions:    {successful_count}",
            f"Failed Extractions:        {failed_count}",
            f"Success Rate:              {overall_success_rate:.1f}%",
            f"Flagged for Review:        {self.total_flagged_for_review}",
            "",
            "=" * 80,
            "QUALITY METRICS",
            "=" * 80,
            f"Average Confidence Score:  {avg_confidence:.3f}",
            f"Min Confidence:            {min(confidence_scores) if confidence_scores else 0:.3f}",
            f"Max Confidence:            {max(confidence_scores) if confidence_scores else 0:.3f}",
            "",
            "=" * 80,
            "PERFORMANCE METRICS",
            "=" * 80,
            f"Total Input Tokens:        {total_input_tokens:,}",
            f"Total Output Tokens:       {total_output_tokens:,}",
            f"Total Tokens:              {total_tokens:,}",
            f"Average Tokens/Extract:    {avg_tokens:,.0f}",
            f"Average Tool Calls:        {avg_tool_calls:.1f}",
            f"Average Conversation Turns: {avg_turns:.1f}",
            "",
            "=" * 80,
            "TOOL USAGE",
            "=" * 80,
        ]

        for tool_name, count in tool_counter.most_common():
            success_count = tool_successes.get(tool_name, 0)
            tool_success_rate = (success_count / count * 100) if count > 0 else 0
            report_lines.append(f"{tool_name:30s} {count:4d} calls  ({tool_success_rate:5.1f}% success)")

        if common_errors:
            report_lines.extend([
                "",
                "=" * 80,
                "COMMON FAILURE PATTERNS",
                "=" * 80,
            ])
            for error, count in common_errors:
                report_lines.append(f"[{count}x] {error[:70]}")

        report_lines.extend([
            "",
            "=" * 80,
            "END OF REPORT",
            "=" * 80,
        ])

        # Save report to file
        report_text = '\n'.join(report_lines)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_text)

        logger.info(f"✓ Report saved to: {report_path}")

        # Print summary to console with Rich
        console.print("\n" + "=" * 80 + "\n")
        console.print(Panel.fit(
            "[bold magenta]Batch Processing Report[/bold magenta]",
            border_style="magenta"
        ))

        # Summary table
        summary_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
        summary_table.add_column("Metric", style="cyan", width=35)
        summary_table.add_column("Value", style="white", width=20)

        summary_table.add_row("Total Processed", str(total_count))
        summary_table.add_row("Successful", f"{successful_count} ({overall_success_rate:.1f}%)")
        summary_table.add_row("Failed", str(failed_count))
        summary_table.add_row("Flagged for Review", str(self.total_flagged_for_review))
        summary_table.add_row("", "")
        summary_table.add_row("Average Confidence", f"{avg_confidence:.3f}")
        summary_table.add_row("Average Tokens", f"{avg_tokens:,.0f}")
        summary_table.add_row("Average Tool Calls", f"{avg_tool_calls:.1f}")
        summary_table.add_row("Average Turns", f"{avg_turns:.1f}")

        console.print(summary_table)

        # Tool usage table
        console.print("\n[bold cyan]Tool Usage:[/bold cyan]")
        tool_table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        tool_table.add_column("Tool", style="cyan", width=30)
        tool_table.add_column("Calls", style="white", width=10)
        tool_table.add_column("Success Rate", style="green", width=15)

        for tool_name, count in tool_counter.most_common():
            success_count = tool_successes.get(tool_name, 0)
            tool_success_rate = (success_count / count * 100) if count > 0 else 0
            tool_table.add_row(tool_name, str(count), f"{tool_success_rate:.1f}%")

        console.print(tool_table)

        console.print(f"\n[green]✓ Full report saved to: {report_path}[/green]\n")


def main():
    """Main function for CLI usage."""
    import argparse

    # Set up logging only when run directly (not when imported)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('batch_processing.log'),
            logging.StreamHandler()
        ]
    )

    parser = argparse.ArgumentParser(
        description="Batch process PLA officer biographical sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process URLs from a file
  python batch_processor.py urls.txt

  # Process URLs and save high-confidence results to database
  python batch_processor.py urls.txt --save-to-db

  # Process with custom rate limit
  python batch_processor.py urls.txt --rate-limit 2.0

  # Process specific URLs
  python batch_processor.py --urls "http://example.com/1" "http://example.com/2"
        """
    )

    parser.add_argument(
        'input_file',
        nargs='?',
        help='File containing URLs (one per line)'
    )
    parser.add_argument(
        '--urls',
        nargs='+',
        help='Process specific URLs directly'
    )
    parser.add_argument(
        '--save-to-db',
        action='store_true',
        help='Save high-confidence results to database'
    )
    parser.add_argument(
        '--require-db',
        action='store_true',
        help='Require database connection'
    )
    parser.add_argument(
        '--rate-limit',
        type=float,
        default=1.0,
        help='Seconds to wait between requests (default: 1.0)'
    )

    args = parser.parse_args()

    # Validate input
    if not args.input_file and not args.urls:
        parser.print_help()
        console.print("\n[red]Error: Provide either input_file or --urls[/red]")
        sys.exit(1)

    # Initialize processor
    try:
        processor = BatchProcessor(
            require_db=args.require_db,
            rate_limit_seconds=args.rate_limit
        )
    except Exception as e:
        console.print(f"[red]Failed to initialize processor: {e}[/red]")
        sys.exit(1)

    # Process URLs
    try:
        if args.urls:
            # Process URLs from command line
            results = processor.process_urls(args.urls, save_to_db=args.save_to_db)
        else:
            # Process URLs from file
            results = processor.process_from_file(args.input_file, save_to_db=args.save_to_db)

        # Generate report
        if results:
            processor.generate_batch_report(results)

        # Exit with appropriate code
        sys.exit(0 if results else 1)

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        logger.error(f"Batch processing failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
