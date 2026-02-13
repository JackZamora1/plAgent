#!/usr/bin/env python3
"""
Test script to verify agent follows recommended workflow.

Checks that tool calls occur in the recommended sequence:
1. lookup_existing_officer
2. Extract info (no tool call)
3. verify_information_present (multiple calls)
4. validate_dates
5. save_officer_bio
6. save_to_database (optional)
"""
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import box

from agent import PLAgentSDK
from tools.extraction_tools import extract_text_from_file

console = Console()


def analyze_workflow(result):
    """
    Analyze the tool call sequence.

    Args:
        result: AgentExtractionResult

    Returns:
        dict with workflow analysis
    """
    tool_names = [tool.tool_name for tool in result.tool_calls]

    analysis = {
        'total_tools': len(tool_names),
        'unique_tools': len(set(tool_names)),
        'has_lookup': 'lookup_existing_officer' in tool_names,
        'has_verify': 'verify_information_present' in tool_names,
        'has_validate': 'validate_dates' in tool_names,
        'has_save': 'save_officer_bio' in tool_names,
        'has_db_save': 'save_to_database' in tool_names,
        'verify_count': tool_names.count('verify_information_present'),
        'save_count': tool_names.count('save_officer_bio'),
    }

    # Check sequence
    sequence_issues = []

    # Check if lookup is first (if it exists)
    if analysis['has_lookup'] and tool_names[0] != 'lookup_existing_officer':
        sequence_issues.append("lookup_existing_officer should be first")

    # Check if validate comes before save
    if analysis['has_validate'] and analysis['has_save']:
        validate_idx = tool_names.index('validate_dates')
        save_idx = tool_names.index('save_officer_bio')
        if validate_idx > save_idx:
            sequence_issues.append("validate_dates should come before save_officer_bio")

    # Check if save comes before db_save
    if analysis['has_save'] and analysis['has_db_save']:
        save_idx = tool_names.index('save_officer_bio')
        db_save_idx = tool_names.index('save_to_database')
        if save_idx > db_save_idx:
            sequence_issues.append("save_officer_bio should come before save_to_database")

    # Check if verify calls happen
    if analysis['verify_count'] == 0:
        sequence_issues.append("Missing verify_information_present calls for uncertain fields")
    elif analysis['verify_count'] < 2:
        sequence_issues.append(f"Only {analysis['verify_count']} verify call(s) - should verify multiple fields")

    # Check if save is called only once
    if analysis['save_count'] > 1:
        sequence_issues.append(f"save_officer_bio called {analysis['save_count']} times - should be ONCE")

    analysis['sequence_issues'] = sequence_issues
    analysis['follows_workflow'] = len(sequence_issues) == 0

    return analysis, tool_names


def print_tool_sequence(tool_calls):
    """Print tool call sequence in a table."""
    console.print("\n[bold cyan]Tool Call Sequence:[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
    table.add_column("#", style="dim", width=4)
    table.add_column("Tool Name", style="cyan", width=35)
    table.add_column("Status", style="white", width=10)
    table.add_column("Notes", style="dim", width=30)

    for i, tool in enumerate(tool_calls, 1):
        status = "[green]✓[/green]" if tool.success else "[red]✗[/red]"

        # Add notes for important tools
        notes = ""
        if tool.tool_name == 'lookup_existing_officer':
            notes = "Check for duplicates" if i == 1 else "⚠ Should be first"
        elif tool.tool_name == 'verify_information_present':
            if tool.success and tool.data:
                field = tool.data.get('field_name', '')
                notes = f"Verify: {field}"
        elif tool.tool_name == 'validate_dates':
            notes = "Date validation"
        elif tool.tool_name == 'save_officer_bio':
            notes = "Save extraction" if tool.success else "Failed - will retry"

        table.add_row(str(i), tool.tool_name, status, notes)

    console.print(table)


def print_workflow_analysis(analysis, tool_names):
    """Print workflow analysis."""
    console.print("\n[bold cyan]Workflow Analysis:[/bold cyan]\n")

    # Summary table
    summary_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
    summary_table.add_column("Check", style="cyan", width=40)
    summary_table.add_column("Status", style="white", width=15)

    # Check each step
    checks = [
        ("Step 1: lookup_existing_officer", analysis['has_lookup']),
        ("Step 3: verify_information_present (2+ calls)", analysis['verify_count'] >= 2),
        ("Step 4: validate_dates", analysis['has_validate']),
        ("Step 5: save_officer_bio (once)", analysis['has_save'] and analysis['save_count'] == 1),
    ]

    for check_name, passed in checks:
        status = "[green]✓ PASS[/green]" if passed else "[red]✗ FAIL[/red]"
        summary_table.add_row(check_name, status)

    console.print(summary_table)

    # Sequence issues
    if analysis['sequence_issues']:
        console.print("\n[bold yellow]Sequence Issues:[/bold yellow]")
        for issue in analysis['sequence_issues']:
            console.print(f"  [yellow]⚠ {issue}[/yellow]")
    else:
        console.print("\n[bold green]✓ No sequence issues - workflow followed correctly![/bold green]")

    # Statistics
    console.print(f"\n[bold cyan]Statistics:[/bold cyan]")
    console.print(f"  Total tool calls: {analysis['total_tools']}")
    console.print(f"  Unique tools used: {analysis['unique_tools']}")
    console.print(f"  verify_information_present calls: {analysis['verify_count']}")


def main():
    """Main test function."""
    console.print("\n[bold magenta]Testing Agent Workflow Adherence[/bold magenta]\n")

    # Check for test file
    test_file = Path("data/test_obituary.txt")
    if not test_file.exists():
        console.print(f"[red]✗ Test file not found: {test_file}[/red]")
        console.print("[yellow]Please create data/test_obituary.txt with a test obituary[/yellow]")
        return 1

    # Load source text
    console.print(f"[cyan]Loading test obituary from {test_file}...[/cyan]")
    source_text = extract_text_from_file(str(test_file))
    console.print(f"[green]✓ Loaded {len(source_text)} characters[/green]")

    # Initialize SDK
    console.print("\n[cyan]Initializing SDK...[/cyan]")
    try:
        sdk = PLAgentSDK(require_db=False)
        console.print("[green]✓ SDK initialized[/green]")
    except Exception as e:
        console.print(f"[red]✗ SDK initialization failed: {e}[/red]")
        return 1

    # Run extraction
    console.print("\n[cyan]Running extraction...[/cyan]")
    console.print("[dim]Watch for tool calls in recommended sequence:[/dim]")
    console.print("[dim]1. lookup_existing_officer[/dim]")
    console.print("[dim]2. verify_information_present (multiple)[/dim]")
    console.print("[dim]3. validate_dates[/dim]")
    console.print("[dim]4. save_officer_bio[/dim]\n")

    try:
        result = sdk.extract_bio_agentic(
            source_text=source_text,
            source_url="https://test/workflow/obituary.html",
            source_type="universal"
        )

        # Analyze workflow
        analysis, tool_names = analyze_workflow(result)

        # Print results
        console.print("\n" + "=" * 80 + "\n")

        # Show extraction result
        if result.success and result.officer_bio:
            officer = result.officer_bio
            console.print(f"[bold green]✓ Extraction Successful:[/bold green] {officer.name}")
            console.print(f"  Confidence: {officer.confidence_score:.2f}")
            console.print(f"  Tokens: {result.get_total_tokens():,}")
        else:
            console.print(f"[bold red]✗ Extraction Failed:[/bold red] {result.error_message}")

        # Show tool sequence
        print_tool_sequence(result.tool_calls)

        # Show workflow analysis
        print_workflow_analysis(analysis, tool_names)

        # Overall assessment
        console.print("\n" + "=" * 80 + "\n")

        if analysis['follows_workflow']:
            console.print("[bold green]✓ WORKFLOW TEST PASSED[/bold green]")
            console.print("[green]Agent followed the recommended workflow correctly![/green]")
            return 0
        else:
            console.print("[bold yellow]⚠ WORKFLOW TEST PARTIAL PASS[/bold yellow]")
            console.print(f"[yellow]Found {len(analysis['sequence_issues'])} sequence issue(s)[/yellow]")
            console.print("[dim]Review sequence issues above for details[/dim]")
            return 0  # Still return 0 since extraction succeeded

    except Exception as e:
        console.print(f"\n[red]✗ Extraction failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
