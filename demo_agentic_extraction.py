#!/usr/bin/env python3
"""Demo script for PLAgentSDK agentic extraction."""
from agent import PLAgentSDK
from tools.extraction_tools import extract_text_from_file
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
import logging
from pathlib import Path

console = Console()


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('extraction.log'),
            logging.StreamHandler()
        ]
    )


def display_result_summary(result):
    """Display extraction result summary."""
    console.print("\n" + "="*80 + "\n")
    console.print("[bold magenta]Extraction Summary[/bold magenta]\n")

    # Status
    status_color = "green" if result.success else "red"
    status_text = "✓ Success" if result.success else "✗ Failed"
    console.print(f"[bold {status_color}]{status_text}[/bold {status_color}]")

    if not result.success:
        console.print(f"[red]Error: {result.error_message}[/red]")
        return

    # Officer info
    if result.officer_bio:
        officer = result.officer_bio

        console.print(f"\n[bold cyan]Officer:[/bold cyan] {officer.name}")
        if officer.pinyin_name:
            console.print(f"[bold]Pinyin:[/bold] {officer.pinyin_name}")
        if officer.hometown:
            console.print(f"[bold]Hometown:[/bold] {officer.hometown}")

        # Dates
        if officer.birth_date or officer.death_date:
            console.print("\n[bold cyan]Dates:[/bold cyan]")
            if officer.birth_date:
                console.print(f"  Birth: {officer.birth_date}")
            if officer.enlistment_date:
                console.print(f"  Enlisted: {officer.enlistment_date}")
            if officer.party_membership_date:
                console.print(f"  CCP Member: {officer.party_membership_date}")
            if officer.death_date:
                console.print(f"  Death: {officer.death_date}")

        # Promotions
        if officer.promotions:
            console.print(f"\n[bold cyan]Promotions:[/bold cyan]")
            for promo in officer.promotions:
                date_str = f" ({promo.date})" if promo.date else ""
                console.print(f"  • {promo.rank}{date_str}")

        # Positions
        if officer.notable_positions:
            console.print(f"\n[bold cyan]Notable Positions:[/bold cyan]")
            for pos in officer.notable_positions:
                console.print(f"  • {pos}")

        # Political
        if officer.congress_participation or officer.cppcc_participation:
            console.print(f"\n[bold cyan]Political Participation:[/bold cyan]")
            if officer.congress_participation:
                for congress in officer.congress_participation:
                    console.print(f"  • CCP Congress: {congress}")
            if officer.cppcc_participation:
                for cppcc in officer.cppcc_participation:
                    console.print(f"  • CPPCC: {cppcc}")

        # Confidence
        console.print(f"\n[bold cyan]Confidence Score:[/bold cyan] {officer.confidence_score:.2f}")

        if officer.extraction_notes:
            console.print(f"\n[bold cyan]Notes:[/bold cyan] {officer.extraction_notes}")

    # Performance metrics
    console.print("\n[bold cyan]Performance Metrics:[/bold cyan]")
    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Conversation Turns", str(result.conversation_turns))
    table.add_row("Tool Calls", str(len(result.tool_calls)))
    table.add_row("Input Tokens", f"{result.total_input_tokens:,}")
    table.add_row("Output Tokens", f"{result.total_output_tokens:,}")
    table.add_row("Total Tokens", f"{result.get_total_tokens():,}")
    table.add_row("Tool Success Rate", f"{result.get_success_rate():.1%}")

    console.print(table)

    # Tool usage breakdown
    console.print("\n[bold cyan]Tool Usage:[/bold cyan]")
    tool_table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    tool_table.add_column("Tool", style="cyan")
    tool_table.add_column("Status", style="white")
    tool_table.add_column("Details", style="dim")

    for tool in result.tool_calls:
        status = "✓" if tool.success else "✗"
        status_color = "green" if tool.success else "red"

        details = ""
        if tool.tool_name == "validate_dates" and tool.success:
            details = "Dates validated"
        elif tool.tool_name == "verify_information_present":
            if tool.data.get('found'):
                details = f"Found: {tool.data.get('field_name')}"
            else:
                details = f"Not found: {tool.data.get('field_name')}"
        elif tool.tool_name == "lookup_existing_officer":
            if tool.data.get('found'):
                details = "Officer exists"
            else:
                details = "New officer"
        elif tool.tool_name == "save_officer_bio":
            details = "Data saved"
        elif not tool.success:
            details = tool.error[:50] if tool.error else "Error"

        tool_table.add_row(
            tool.tool_name,
            f"[{status_color}]{status}[/{status_color}]",
            details
        )

    console.print(tool_table)


def main():
    """Main demo function."""
    console.print(Panel.fit(
        "[bold magenta]PLAgentSDK - Agentic Extraction Demo[/bold magenta]\n"
        "Demonstrates automatic tool use for officer bio extraction",
        border_style="magenta"
    ))

    # Setup logging
    setup_logging()

    # Initialize SDK
    console.print("\n[cyan]Initializing PLAgentSDK...[/cyan]")
    try:
        sdk = PLAgentSDK(require_db=False)
        console.print("[green]✓ SDK initialized[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed to initialize SDK: {e}[/red]")
        return 1

    # Load test obituary
    test_file = Path(__file__).parent / "data" / "test_obituary.txt"
    if not test_file.exists():
        console.print(f"[red]✗ Test file not found: {test_file}[/red]")
        return 1

    console.print(f"\n[cyan]Loading obituary from {test_file}...[/cyan]")
    source_text = extract_text_from_file(str(test_file))
    console.print(f"[green]✓ Loaded {len(source_text)} characters[/green]")

    # Display source text
    console.print("\n[bold cyan]Source Text:[/bold cyan]")
    console.print(Panel(source_text, border_style="dim"))

    # Extract biography
    console.print("\n[bold cyan]Starting Agentic Extraction...[/bold cyan]")
    console.print("[dim]Claude will use tools automatically to extract and validate data[/dim]")
    console.print("[dim]Using universal profile - adapts to any source type[/dim]\n")

    try:
        result = sdk.extract_bio_agentic(
            source_text=source_text,
            source_url="https://www.news.cn/test/obituary.html",
            source_type="universal"
        )

        # Display results
        display_result_summary(result)

        # Save result
        if result.success:
            output_file = sdk.save_result_to_file(result)
            console.print(f"\n[green]✓ Full results saved to {output_file}[/green]")

        return 0 if result.success else 1

    except Exception as e:
        console.print(f"\n[red]✗ Extraction failed: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit(main())
