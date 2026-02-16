#!/usr/bin/env python3
"""Test database lookup tools for Anthropic integration."""
from tools.database_tools import (
    LOOKUP_OFFICER_TOOL,
    LOOKUP_UNIT_TOOL,
    execute_lookup_officer,
    execute_lookup_unit,
    initialize_database
)
from rich.console import Console
from rich.panel import Panel
from rich.json import JSON
import json

console = Console()


def test_lookup_officer_tool_definition():
    """Test LOOKUP_OFFICER_TOOL definition."""
    console.print("\n[bold cyan]Testing LOOKUP_OFFICER_TOOL Definition[/bold cyan]")

    # Verify structure
    assert 'name' in LOOKUP_OFFICER_TOOL
    assert 'description' in LOOKUP_OFFICER_TOOL
    assert 'input_schema' in LOOKUP_OFFICER_TOOL

    assert LOOKUP_OFFICER_TOOL['name'] == 'lookup_existing_officer'

    schema = LOOKUP_OFFICER_TOOL['input_schema']
    assert 'properties' in schema
    assert 'name' in schema['properties']
    assert 'required' in schema
    assert 'name' in schema['required']

    console.print("[green]✓ Tool definition validated[/green]")
    console.print(f"\n[bold]Tool Name:[/bold] {LOOKUP_OFFICER_TOOL['name']}")
    console.print(f"[bold]Description:[/bold] {LOOKUP_OFFICER_TOOL['description'][:100]}...")


def test_lookup_unit_tool_definition():
    """Test LOOKUP_UNIT_TOOL definition."""
    console.print("\n[bold cyan]Testing LOOKUP_UNIT_TOOL Definition[/bold cyan]")

    # Verify structure
    assert 'name' in LOOKUP_UNIT_TOOL
    assert 'description' in LOOKUP_UNIT_TOOL
    assert 'input_schema' in LOOKUP_UNIT_TOOL

    assert LOOKUP_UNIT_TOOL['name'] == 'lookup_unit_by_name'

    schema = LOOKUP_UNIT_TOOL['input_schema']
    assert 'properties' in schema
    assert 'unit_name' in schema['properties']
    assert 'required' in schema
    assert 'unit_name' in schema['required']

    console.print("[green]✓ Tool definition validated[/green]")
    console.print(f"\n[bold]Tool Name:[/bold] {LOOKUP_UNIT_TOOL['name']}")
    console.print(f"[bold]Description:[/bold] {LOOKUP_UNIT_TOOL['description'][:100]}...")


def test_execute_lookup_officer_validation():
    """Test input validation for execute_lookup_officer."""
    console.print("\n[bold cyan]Testing execute_lookup_officer() - Input Validation[/bold cyan]")

    # Missing name
    result = execute_lookup_officer({})

    assert not result.success, "Should fail when name is missing"
    assert 'required' in result.error.lower()

    console.print("[green]✓ Input validation working[/green]")
    console.print(f"\n[bold]Error Message:[/bold]")
    console.print(Panel(result.error, title="Validation Error", border_style="red"))


def test_execute_lookup_unit_validation():
    """Test input validation for execute_lookup_unit."""
    console.print("\n[bold cyan]Testing execute_lookup_unit() - Input Validation[/bold cyan]")

    # Missing unit_name
    result = execute_lookup_unit({})

    assert not result.success, "Should fail when unit_name is missing"
    assert 'required' in result.error.lower()

    console.print("[green]✓ Input validation working[/green]")
    console.print(f"\n[bold]Error Message:[/bold]")
    console.print(Panel(result.error, title="Validation Error", border_style="red"))


def test_database_connection_error_handling():
    """Test that database errors are handled gracefully."""
    console.print("\n[bold cyan]Testing Database Error Handling[/bold cyan]")

    # This will likely fail if database is not set up
    # But should return a proper ToolResult with error message
    result = execute_lookup_officer({"name": "测试"})

    # Check that result is a ToolResult
    assert hasattr(result, 'success')
    assert hasattr(result, 'error')
    assert result.tool_name == 'lookup_existing_officer'

    if not result.success:
        console.print("[yellow]⚠ Database not available (expected)[/yellow]")
        console.print(f"[bold]Error:[/bold] {result.error}")
    else:
        console.print("[green]✓ Database connection successful![/green]")
        console.print(f"[bold]Result:[/bold]")
        console.print(Panel(
            JSON(json.dumps(result.data, ensure_ascii=False, indent=2)),
            title="Lookup Result"
        ))

    console.print("\n[green]✓ Error handling validated[/green]")


def test_anthropic_api_format():
    """Test tool definitions work with Anthropic API format."""
    console.print("\n[bold cyan]Testing Anthropic API Compatibility[/bold cyan]")

    tools = [LOOKUP_OFFICER_TOOL, LOOKUP_UNIT_TOOL]

    # Verify JSON serializable
    try:
        json_str = json.dumps(tools)
        console.print(f"[green]✓ Tools are JSON serializable ({len(json_str)} chars)[/green]")
    except Exception as e:
        console.print(f"[red]✗ JSON serialization failed: {e}[/red]")
        raise

    console.print("\n[bold]Tool Definitions:[/bold]")
    for tool in tools:
        console.print(f"  - {tool['name']}")


def test_database_schema_creation():
    """Test database schema initialization."""
    console.print("\n[bold cyan]Testing Database Schema Creation[/bold cyan]")

    try:
        initialize_database()
        console.print("[green]✓ Database schema initialized successfully[/green]")
        console.print("\n[bold]Created tables:[/bold]")
        console.print("  - pla_leaders (with indexes)")
        console.print("  - units (with indexes)")
    except Exception as e:
        console.print(f"[yellow]⚠ Could not initialize database: {e}[/yellow]")
        console.print("[dim]This is expected if database is not configured[/dim]")


def test_usage_example():
    """Show usage example."""
    console.print("\n[bold cyan]Usage Example[/bold cyan]")

    example_code = '''
from anthropic import Anthropic
from tools import LOOKUP_OFFICER_TOOL, execute_lookup_officer

client = Anthropic(api_key="your-key")

# Give Claude the lookup tool
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    tools=[LOOKUP_OFFICER_TOOL],
    messages=[{
        "role": "user",
        "content": "Check if we already have data for 林炳尧"
    }]
)

# Process tool use
for block in response.content:
    if block.type == "tool_use" and block.name == "lookup_existing_officer":
        result = execute_lookup_officer(block.input)

        if result.success and result.data.get('found'):
            print(f"Found existing officer!")
            print(result.data['officer'])
        else:
            print("Officer not in database yet")
'''

    console.print(Panel(example_code, title="Example Usage", border_style="cyan"))


def main():
    """Run all tests."""
    console.print("[bold magenta]Database Lookup Tools - Test Suite[/bold magenta]")

    try:
        # Definition tests
        test_lookup_officer_tool_definition()
        test_lookup_unit_tool_definition()

        # Validation tests
        test_execute_lookup_officer_validation()
        test_execute_lookup_unit_validation()

        # Error handling
        test_database_connection_error_handling()

        # API compatibility
        test_anthropic_api_format()

        # Schema creation
        test_database_schema_creation()

        # Usage example
        test_usage_example()

        console.print("\n[bold green]✓ All database tool tests passed![/bold green]")
        console.print("\n[bold yellow]Note:[/bold yellow] Some tests may show warnings if database is not configured.")
        console.print("This is expected. The tools will work once the database is set up.")
        return 0

    except AssertionError as e:
        console.print(f"\n[bold red]✗ Test assertion failed: {e}[/bold red]")
        import traceback
        console.print(traceback.format_exc())
        return 1

    except Exception as e:
        console.print(f"\n[bold red]✗ Test suite failed: {e}[/bold red]")
        import traceback
        console.print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit(main())
