"""Debug tool for analyzing PLA Agent SDK extraction results."""
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import Counter

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.text import Text
from rich import box
from rich.columns import Columns

from schema import AgentExtractionResult, OfficerBio, ToolResult

console = Console()


def load_extraction_result(json_file: str) -> Dict[str, Any]:
    """
    Load extraction result from JSON file.

    Args:
        json_file: Path to JSON file

    Returns:
        Dictionary containing extraction result data

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    file_path = Path(json_file)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {json_file}")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data


def replay_conversation(json_file: str):
    """
    Replay the entire extraction conversation step-by-step.

    Shows:
    - Initial prompt sent to Claude
    - Each tool call Claude made
    - Tool execution results
    - Final extraction outcome

    Args:
        json_file: Path to saved AgentExtractionResult JSON file
    """
    console.print("\n[bold cyan]═══ Conversation Replay ═══[/bold cyan]\n")

    try:
        data = load_extraction_result(json_file)
    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return
    except json.JSONDecodeError as e:
        console.print(f"[bold red]Error:[/bold red] Invalid JSON file: {e}")
        return

    # Extract metadata
    success = data.get('success', False)
    conversation_turns = data.get('conversation_turns', 0)
    total_tokens = data.get('total_input_tokens', 0) + data.get('total_output_tokens', 0)

    # Header
    status_color = "green" if success else "red"
    status_text = "SUCCESS" if success else "FAILED"

    console.print(Panel(
        f"[{status_color}]Status: {status_text}[/{status_color}]\n"
        f"Conversation Turns: {conversation_turns}\n"
        f"Total Tokens: {total_tokens:,}",
        title="Extraction Overview",
        border_style="cyan"
    ))

    # Show officer bio if present
    officer_bio = data.get('officer_bio')
    if officer_bio:
        console.print("\n[bold yellow]📋 Extracted Officer Information[/bold yellow]\n")

        bio_table = Table(show_header=False, box=box.SIMPLE)
        bio_table.add_column("Field", style="cyan", width=25)
        bio_table.add_column("Value", style="white")

        bio_table.add_row("Name", officer_bio.get('name', 'N/A'))
        if officer_bio.get('pinyin_name'):
            bio_table.add_row("Pinyin Name", officer_bio['pinyin_name'])
        if officer_bio.get('hometown'):
            bio_table.add_row("Hometown", officer_bio['hometown'])
        if officer_bio.get('birth_date'):
            bio_table.add_row("Birth Date", officer_bio['birth_date'])
        if officer_bio.get('death_date'):
            bio_table.add_row("Death Date", officer_bio['death_date'])
        if officer_bio.get('enlistment_date'):
            bio_table.add_row("Enlistment Date", officer_bio['enlistment_date'])
        if officer_bio.get('party_membership_date'):
            bio_table.add_row("Party Membership", officer_bio['party_membership_date'])

        bio_table.add_row("Confidence Score", f"{officer_bio.get('confidence_score', 0.0):.2f}")

        console.print(bio_table)

    # Tool call replay
    tool_calls = data.get('tool_calls', [])

    if not tool_calls:
        console.print("\n[yellow]No tool calls were made during extraction[/yellow]")
        return

    console.print(f"\n[bold magenta]🔧 Tool Execution Timeline ({len(tool_calls)} calls)[/bold magenta]\n")

    for idx, tool_call in enumerate(tool_calls, 1):
        tool_name = tool_call.get('tool_name', 'unknown')
        success = tool_call.get('success', False)
        tool_data = tool_call.get('data', {})
        error = tool_call.get('error')
        timestamp = tool_call.get('timestamp', 'unknown')

        # Status indicator
        status_icon = "✓" if success else "✗"
        status_color = "green" if success else "red"

        # Build tool call panel
        panel_content = f"[{status_color}]{status_icon}[/{status_color}] [bold]{tool_name}[/bold]\n"
        panel_content += f"[dim]Timestamp: {timestamp}[/dim]\n\n"

        if success:
            # Show key data from successful tool calls
            if tool_name == "validate_dates":
                valid = tool_data.get('valid', False)
                panel_content += f"Valid: [{'green' if valid else 'red'}]{valid}[/]\n"
                if tool_data.get('issues'):
                    panel_content += f"Issues: {', '.join(tool_data['issues'])}\n"

            elif tool_name == "verify_information_present":
                found = tool_data.get('found', False)
                field_name = tool_data.get('field_name', 'unknown')
                panel_content += f"Field: [cyan]{field_name}[/cyan]\n"
                panel_content += f"Found: [{'green' if found else 'yellow'}]{found}[/]\n"
                if tool_data.get('evidence'):
                    evidence = tool_data['evidence'][:100]
                    panel_content += f"Evidence: [dim]{evidence}...[/dim]\n"

            elif tool_name == "lookup_existing_officer":
                found = tool_data.get('found', False)
                officer_name = tool_data.get('officer_name', 'unknown')
                panel_content += f"Officer: [cyan]{officer_name}[/cyan]\n"
                panel_content += f"Found in DB: [{'green' if found else 'yellow'}]{found}[/]\n"

            elif tool_name == "lookup_unit_by_name":
                found = tool_data.get('found', False)
                unit_name = tool_data.get('unit_name', 'unknown')
                panel_content += f"Unit: [cyan]{unit_name}[/cyan]\n"
                panel_content += f"Found: [{'green' if found else 'yellow'}]{found}[/]\n"

            elif tool_name == "save_officer_bio":
                saved_officer = tool_data.get('officer_bio', {})
                panel_content += f"Saved: [green]{saved_officer.get('name', 'unknown')}[/green]\n"
                panel_content += f"Confidence: {saved_officer.get('confidence_score', 0.0):.2f}\n"
        else:
            # Show error for failed calls
            panel_content += f"[red]Error: {error}[/red]\n"

        console.print(Panel(
            panel_content,
            title=f"[bold]Step {idx}[/bold]",
            border_style=status_color,
            padding=(1, 2)
        ))

    # Final outcome
    console.print("\n[bold cyan]═══ Final Outcome ═══[/bold cyan]\n")

    if success:
        console.print("[bold green]✓ Extraction completed successfully[/bold green]")
        if officer_bio:
            console.print(f"Officer: [cyan]{officer_bio.get('name')}[/cyan]")
            console.print(f"Confidence: {officer_bio.get('confidence_score', 0.0):.2f}")
    else:
        error_msg = data.get('error_message', 'Unknown error')
        console.print(f"[bold red]✗ Extraction failed[/bold red]")
        console.print(f"[red]Error: {error_msg}[/red]")

    console.print()


def analyze_tool_usage(json_file: str):
    """
    Analyze tool usage patterns and generate statistics.

    Shows:
    - Tool call frequency
    - Success rates per tool
    - Token usage patterns
    - Extraction insights

    Args:
        json_file: Path to saved AgentExtractionResult JSON file
    """
    console.print("\n[bold cyan]═══ Tool Usage Analysis ═══[/bold cyan]\n")

    try:
        data = load_extraction_result(json_file)
    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return
    except json.JSONDecodeError as e:
        console.print(f"[bold red]Error:[/bold red] Invalid JSON file: {e}")
        return

    tool_calls = data.get('tool_calls', [])

    if not tool_calls:
        console.print("[yellow]No tool calls found in this extraction[/yellow]")
        return

    # Gather statistics
    tool_names = [tc.get('tool_name') for tc in tool_calls]
    tool_counter = Counter(tool_names)

    successful_calls = sum(1 for tc in tool_calls if tc.get('success', False))
    failed_calls = len(tool_calls) - successful_calls
    overall_success_rate = successful_calls / len(tool_calls) if tool_calls else 0

    # Per-tool success rates
    tool_success_rates = {}
    for tool_name in set(tool_names):
        tool_total = sum(1 for tc in tool_calls if tc.get('tool_name') == tool_name)
        tool_successful = sum(
            1 for tc in tool_calls
            if tc.get('tool_name') == tool_name and tc.get('success', False)
        )
        tool_success_rates[tool_name] = (tool_successful / tool_total) if tool_total > 0 else 0

    # Token usage
    total_input_tokens = data.get('total_input_tokens', 0)
    total_output_tokens = data.get('total_output_tokens', 0)
    total_tokens = total_input_tokens + total_output_tokens
    conversation_turns = data.get('conversation_turns', 0)

    avg_tokens_per_turn = total_tokens / conversation_turns if conversation_turns > 0 else 0

    # Display statistics

    # 1. Overall metrics
    metrics_table = Table(title="Overall Metrics", box=box.ROUNDED)
    metrics_table.add_column("Metric", style="cyan")
    metrics_table.add_column("Value", style="white", justify="right")

    metrics_table.add_row("Total Tool Calls", str(len(tool_calls)))
    metrics_table.add_row("Successful Calls", f"[green]{successful_calls}[/green]")
    metrics_table.add_row("Failed Calls", f"[red]{failed_calls}[/red]")
    metrics_table.add_row("Overall Success Rate", f"{overall_success_rate:.1%}")
    metrics_table.add_row("Conversation Turns", str(conversation_turns))
    metrics_table.add_row("Total Tokens", f"{total_tokens:,}")
    metrics_table.add_row("Input Tokens", f"{total_input_tokens:,}")
    metrics_table.add_row("Output Tokens", f"{total_output_tokens:,}")
    metrics_table.add_row("Avg Tokens/Turn", f"{avg_tokens_per_turn:.0f}")

    console.print(metrics_table)
    console.print()

    # 2. Tool frequency
    freq_table = Table(title="Tool Call Frequency", box=box.ROUNDED)
    freq_table.add_column("Tool Name", style="cyan")
    freq_table.add_column("Count", style="white", justify="right")
    freq_table.add_column("Percentage", style="yellow", justify="right")
    freq_table.add_column("Success Rate", style="green", justify="right")

    for tool_name, count in tool_counter.most_common():
        percentage = (count / len(tool_calls)) * 100
        success_rate = tool_success_rates.get(tool_name, 0)

        freq_table.add_row(
            tool_name,
            str(count),
            f"{percentage:.1f}%",
            f"{success_rate:.1%}"
        )

    console.print(freq_table)
    console.print()

    # 3. Tool execution timeline
    console.print("[bold magenta]Tool Execution Order[/bold magenta]\n")

    timeline = " → ".join([
        f"[{'green' if tc.get('success') else 'red'}]{tc.get('tool_name', '?')}[/]"
        for tc in tool_calls
    ])
    console.print(Panel(timeline, border_style="cyan"))
    console.print()

    # 4. Insights and patterns
    console.print("[bold yellow]📊 Insights & Patterns[/bold yellow]\n")

    insights = []

    # Check for common patterns
    if "validate_dates" in tool_names:
        insights.append("✓ Agent validated dates for chronological consistency")

    if "verify_information_present" in tool_names:
        verify_count = tool_counter.get("verify_information_present", 0)
        insights.append(f"✓ Agent verified {verify_count} field(s) to prevent hallucination")

    if "lookup_existing_officer" in tool_names:
        insights.append("✓ Agent checked for duplicate officers in database")

    if "save_officer_bio" in tool_names:
        save_successful = any(
            tc.get('tool_name') == 'save_officer_bio' and tc.get('success')
            for tc in tool_calls
        )
        if save_successful:
            insights.append("[green]✓ Officer bio was successfully saved[/green]")
        else:
            insights.append("[red]✗ Officer bio save failed[/red]")
    else:
        insights.append("[yellow]⚠ Agent never called save_officer_bio[/yellow]")

    # Check for repeated failed calls
    failed_tools = [
        tc.get('tool_name')
        for tc in tool_calls
        if not tc.get('success', False)
    ]
    if failed_tools:
        failed_counter = Counter(failed_tools)
        for tool, count in failed_counter.items():
            if count > 1:
                insights.append(f"[red]⚠ '{tool}' failed {count} times[/red]")

    # Token efficiency
    if avg_tokens_per_turn > 5000:
        insights.append("[yellow]⚠ High token usage per turn - consider optimizing prompts[/yellow]")
    elif avg_tokens_per_turn < 2000:
        insights.append("[green]✓ Efficient token usage[/green]")

    for insight in insights:
        console.print(f"  {insight}")

    console.print()


def compare_extractions(file1: str, file2: str):
    """
    Compare two extraction results side-by-side.

    Shows:
    - Field-by-field comparison
    - Differences highlighted
    - Confidence score comparison
    - Tool usage comparison

    Args:
        file1: Path to first extraction result
        file2: Path to second extraction result
    """
    console.print("\n[bold cyan]═══ Extraction Comparison ═══[/bold cyan]\n")

    try:
        data1 = load_extraction_result(file1)
        data2 = load_extraction_result(file2)
    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return
    except json.JSONDecodeError as e:
        console.print(f"[bold red]Error:[/bold red] Invalid JSON file: {e}")
        return

    # Extract officer bios
    bio1 = data1.get('officer_bio', {})
    bio2 = data2.get('officer_bio', {})

    # File names for display
    name1 = Path(file1).name
    name2 = Path(file2).name

    # 1. Officer Bio Comparison
    console.print("[bold yellow]📋 Officer Bio Comparison[/bold yellow]\n")

    bio_table = Table(box=box.ROUNDED)
    bio_table.add_column("Field", style="cyan", width=25)
    bio_table.add_column(name1, style="white", width=35)
    bio_table.add_column(name2, style="white", width=35)
    bio_table.add_column("Match", style="dim", width=8)

    # Compare key fields
    fields_to_compare = [
        'name', 'pinyin_name', 'hometown', 'birth_date', 'death_date',
        'enlistment_date', 'party_membership_date', 'retirement_date',
        'wife_name', 'confidence_score'
    ]

    differences_count = 0

    for field in fields_to_compare:
        val1 = bio1.get(field)
        val2 = bio2.get(field)

        # Format values
        val1_str = str(val1) if val1 is not None else "[dim]null[/dim]"
        val2_str = str(val2) if val2 is not None else "[dim]null[/dim]"

        # Check if they match
        match = val1 == val2
        match_icon = "[green]✓[/green]" if match else "[red]✗[/red]"

        if not match:
            differences_count += 1
            # Highlight differences
            val1_str = f"[yellow]{val1_str}[/yellow]"
            val2_str = f"[yellow]{val2_str}[/yellow]"

        bio_table.add_row(field, val1_str, val2_str, match_icon)

    console.print(bio_table)
    console.print()

    # 2. List fields comparison (promotions, positions, etc.)
    console.print("[bold yellow]📝 List Fields Comparison[/bold yellow]\n")

    list_fields = ['promotions', 'notable_positions', 'congress_participation',
                   'cppcc_participation', 'awards']

    for field in list_fields:
        list1 = bio1.get(field, []) or []
        list2 = bio2.get(field, []) or []

        if not list1 and not list2:
            continue

        console.print(f"[cyan]{field}:[/cyan]")
        console.print(f"  {name1}: {len(list1)} item(s)")
        console.print(f"  {name2}: {len(list2)} item(s)")

        if list1 != list2:
            console.print("  [yellow]⚠ Lists differ[/yellow]")
        else:
            console.print("  [green]✓ Lists match[/green]")

        console.print()

    # 3. Performance Comparison
    console.print("[bold yellow]⚡ Performance Comparison[/bold yellow]\n")

    perf_table = Table(box=box.ROUNDED)
    perf_table.add_column("Metric", style="cyan")
    perf_table.add_column(name1, style="white", justify="right")
    perf_table.add_column(name2, style="white", justify="right")
    perf_table.add_column("Diff", style="yellow", justify="right")

    # Metrics to compare
    metrics = [
        ('conversation_turns', 'Conversation Turns'),
        ('total_input_tokens', 'Input Tokens'),
        ('total_output_tokens', 'Output Tokens'),
    ]

    for key, label in metrics:
        val1 = data1.get(key, 0)
        val2 = data2.get(key, 0)
        diff = val2 - val1
        diff_str = f"+{diff}" if diff > 0 else str(diff)

        if key.endswith('_tokens'):
            val1_str = f"{val1:,}"
            val2_str = f"{val2:,}"
        else:
            val1_str = str(val1)
            val2_str = str(val2)

        perf_table.add_row(label, val1_str, val2_str, diff_str)

    # Total tokens
    total1 = data1.get('total_input_tokens', 0) + data1.get('total_output_tokens', 0)
    total2 = data2.get('total_input_tokens', 0) + data2.get('total_output_tokens', 0)
    total_diff = total2 - total1
    total_diff_str = f"+{total_diff:,}" if total_diff > 0 else f"{total_diff:,}"
    perf_table.add_row("Total Tokens", f"{total1:,}", f"{total2:,}", total_diff_str)

    console.print(perf_table)
    console.print()

    # 4. Tool Usage Comparison
    console.print("[bold yellow]🔧 Tool Usage Comparison[/bold yellow]\n")

    tools1 = [tc.get('tool_name') for tc in data1.get('tool_calls', [])]
    tools2 = [tc.get('tool_name') for tc in data2.get('tool_calls', [])]

    tool_counter1 = Counter(tools1)
    tool_counter2 = Counter(tools2)

    all_tools = set(tools1 + tools2)

    if all_tools:
        tool_table = Table(box=box.ROUNDED)
        tool_table.add_column("Tool", style="cyan")
        tool_table.add_column(name1, style="white", justify="right")
        tool_table.add_column(name2, style="white", justify="right")

        for tool in sorted(all_tools):
            count1 = tool_counter1.get(tool, 0)
            count2 = tool_counter2.get(tool, 0)
            tool_table.add_row(tool, str(count1), str(count2))

        console.print(tool_table)
    else:
        console.print("[dim]No tool calls in either extraction[/dim]")

    console.print()

    # 5. Summary
    console.print("[bold cyan]═══ Summary ═══[/bold cyan]\n")

    if differences_count == 0:
        console.print("[bold green]✓ All officer bio fields match![/bold green]")
    else:
        console.print(f"[bold yellow]⚠ {differences_count} field(s) differ[/bold yellow]")

    # Confidence comparison
    conf1 = bio1.get('confidence_score', 0.0)
    conf2 = bio2.get('confidence_score', 0.0)

    if conf1 > conf2:
        console.print(f"Higher confidence: [cyan]{name1}[/cyan] ({conf1:.2f} vs {conf2:.2f})")
    elif conf2 > conf1:
        console.print(f"Higher confidence: [cyan]{name2}[/cyan] ({conf2:.2f} vs {conf1:.2f})")
    else:
        console.print(f"Equal confidence: {conf1:.2f}")

    # Token efficiency
    if total1 < total2:
        savings = total2 - total1
        console.print(f"More efficient: [cyan]{name1}[/cyan] (saved {savings:,} tokens)")
    elif total2 < total1:
        savings = total1 - total2
        console.print(f"More efficient: [cyan]{name2}[/cyan] (saved {savings:,} tokens)")
    else:
        console.print("Equal token usage")

    console.print()


def main():
    """Main CLI interface."""
    if len(sys.argv) < 2:
        console.print("[bold cyan]PLA Agent SDK - Debug Tool[/bold cyan]\n")
        console.print("Usage:")
        console.print("  [yellow]python debug_agent.py replay <json_file>[/yellow]")
        console.print("    Replay extraction conversation step-by-step\n")
        console.print("  [yellow]python debug_agent.py analyze <json_file>[/yellow]")
        console.print("    Analyze tool usage and generate statistics\n")
        console.print("  [yellow]python debug_agent.py compare <file1> <file2>[/yellow]")
        console.print("    Compare two extraction results side-by-side\n")
        console.print("Examples:")
        console.print("  python debug_agent.py replay output/test_extraction.json")
        console.print("  python debug_agent.py analyze output/林炳尧_20250210_220500.json")
        console.print("  python debug_agent.py compare output/v1.json output/v2.json")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "replay":
        if len(sys.argv) < 3:
            console.print("[bold red]Error:[/bold red] Missing JSON file argument")
            console.print("Usage: python debug_agent.py replay <json_file>")
            sys.exit(1)
        replay_conversation(sys.argv[2])

    elif command == "analyze":
        if len(sys.argv) < 3:
            console.print("[bold red]Error:[/bold red] Missing JSON file argument")
            console.print("Usage: python debug_agent.py analyze <json_file>")
            sys.exit(1)
        analyze_tool_usage(sys.argv[2])

    elif command == "compare":
        if len(sys.argv) < 4:
            console.print("[bold red]Error:[/bold red] Missing file arguments")
            console.print("Usage: python debug_agent.py compare <file1> <file2>")
            sys.exit(1)
        compare_extractions(sys.argv[2], sys.argv[3])

    else:
        console.print(f"[bold red]Error:[/bold red] Unknown command '{command}'")
        console.print("Valid commands: replay, analyze, compare")
        sys.exit(1)


if __name__ == "__main__":
    main()
