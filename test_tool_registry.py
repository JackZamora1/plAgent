#!/usr/bin/env python3
"""Test tool registry functionality."""
from tools import (
    TOOL_REGISTRY,
    TOOL_EXECUTORS,
    get_all_tools,
    execute_tool,
    get_tool_names,
    get_tool_definition,
    get_tools_by_category,
    EXTRACTION_TOOLS,
    VALIDATION_TOOLS,
    DATABASE_TOOLS
)
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import json

console = Console()


def test_tool_registry_structure():
    """Test TOOL_REGISTRY structure."""
    console.print("\n[bold cyan]Testing TOOL_REGISTRY Structure[/bold cyan]")

    # Verify registry is a dict
    assert isinstance(TOOL_REGISTRY, dict), "TOOL_REGISTRY should be a dict"

    # Verify all entries have required fields
    for tool_name, tool_def in TOOL_REGISTRY.items():
        assert 'name' in tool_def, f"{tool_name} missing 'name' field"
        assert 'description' in tool_def, f"{tool_name} missing 'description'"
        assert 'input_schema' in tool_def, f"{tool_name} missing 'input_schema'"

        # Verify name matches key
        assert tool_def['name'] == tool_name, f"Name mismatch for {tool_name}"

    console.print(f"[green]✓ Registry has {len(TOOL_REGISTRY)} tools[/green]")

    # Create table of tools
    table = Table(title="Registered Tools")
    table.add_column("Tool Name", style="cyan")
    table.add_column("Description", style="white")

    for tool_name, tool_def in TOOL_REGISTRY.items():
        desc = tool_def['description'][:60] + "..." if len(tool_def['description']) > 60 else tool_def['description']
        table.add_row(tool_name, desc)

    console.print(table)


def test_tool_executors_structure():
    """Test TOOL_EXECUTORS structure."""
    console.print("\n[bold cyan]Testing TOOL_EXECUTORS Structure[/bold cyan]")

    # Verify executors is a dict
    assert isinstance(TOOL_EXECUTORS, dict), "TOOL_EXECUTORS should be a dict"

    # Verify all executors are callable
    for tool_name, executor in TOOL_EXECUTORS.items():
        assert callable(executor), f"Executor for {tool_name} is not callable"

    # Verify registry and executors match
    assert set(TOOL_REGISTRY.keys()) == set(TOOL_EXECUTORS.keys()), \
        "Registry and executors should have same keys"

    console.print(f"[green]✓ All {len(TOOL_EXECUTORS)} executors are callable[/green]")
    console.print(f"[green]✓ Registry and executors keys match[/green]")


def test_get_all_tools():
    """Test get_all_tools() function."""
    console.print("\n[bold cyan]Testing get_all_tools()[/bold cyan]")

    tools = get_all_tools()

    # Verify it's a list
    assert isinstance(tools, list), "get_all_tools should return a list"

    # Verify count matches registry
    assert len(tools) == len(TOOL_REGISTRY), "Count should match registry"

    # Verify all tools are valid
    for tool in tools:
        assert 'name' in tool
        assert 'description' in tool
        assert 'input_schema' in tool

    console.print(f"[green]✓ Returns {len(tools)} tool definitions[/green]")

    # Verify it's JSON serializable (required for Anthropic API)
    try:
        json_str = json.dumps(tools)
        console.print(f"[green]✓ All tools are JSON serializable ({len(json_str)} chars)[/green]")
    except Exception as e:
        console.print(f"[red]✗ JSON serialization failed: {e}[/red]")
        raise


def test_get_tool_names():
    """Test get_tool_names() function."""
    console.print("\n[bold cyan]Testing get_tool_names()[/bold cyan]")

    names = get_tool_names()

    assert isinstance(names, list), "Should return a list"
    assert len(names) == len(TOOL_REGISTRY), "Count should match registry"

    expected_names = [
        "save_officer_bio",
        "validate_dates",
        "verify_information_present",
        "lookup_existing_officer",
        "lookup_unit_by_name"
    ]

    for name in expected_names:
        assert name in names, f"{name} should be in tool names"

    console.print(f"[green]✓ Returns {len(names)} tool names[/green]")
    console.print(f"[bold]Tool names:[/bold] {', '.join(names)}")


def test_get_tool_definition():
    """Test get_tool_definition() function."""
    console.print("\n[bold cyan]Testing get_tool_definition()[/bold cyan]")

    # Get a valid tool definition
    tool_def = get_tool_definition("validate_dates")

    assert tool_def['name'] == "validate_dates"
    assert 'description' in tool_def
    assert 'input_schema' in tool_def

    console.print("[green]✓ Successfully retrieved tool definition[/green]")
    console.print(f"[bold]Tool:[/bold] {tool_def['name']}")
    console.print(f"[bold]Description:[/bold] {tool_def['description'][:100]}...")

    # Test invalid tool name
    try:
        get_tool_definition("nonexistent_tool")
        console.print("[red]✗ Should have raised KeyError[/red]")
        assert False
    except KeyError:
        console.print("[green]✓ Raises KeyError for unknown tool[/green]")


def test_execute_tool_success():
    """Test execute_tool() with valid input."""
    console.print("\n[bold cyan]Testing execute_tool() - Success Case[/bold cyan]")

    # Test validate_dates tool
    result = execute_tool(
        "validate_dates",
        {
            "birth_date": "1943",
            "enlistment_date": "1961",
            "promotions": [
                {"rank": "少将", "date": "1995"}
            ]
        }
    )

    assert result.success, "Should succeed with valid dates"
    assert result.tool_name == "validate_dates"
    assert result.error is None

    console.print("[green]✓ Tool executed successfully[/green]")
    console.print(f"[bold]Result:[/bold] {result.data['message']}")


def test_execute_tool_validation_error():
    """Test execute_tool() with invalid input."""
    console.print("\n[bold cyan]Testing execute_tool() - Validation Error[/bold cyan]")

    # Test with conflicting dates
    result = execute_tool(
        "validate_dates",
        {
            "birth_date": "2000",
            "death_date": "1990"  # Death before birth!
        }
    )

    assert not result.success, "Should fail with invalid dates"
    assert "death" in result.error.lower()
    assert "birth" in result.error.lower()

    console.print("[green]✓ Validation error handled correctly[/green]")
    console.print(f"[bold]Error:[/bold] {result.error[:100]}...")


def test_execute_tool_unknown():
    """Test execute_tool() with unknown tool name."""
    console.print("\n[bold cyan]Testing execute_tool() - Unknown Tool[/bold cyan]")

    result = execute_tool("nonexistent_tool", {})

    assert not result.success, "Should fail for unknown tool"
    assert "unknown tool" in result.error.lower()
    assert result.tool_name == "nonexistent_tool"

    console.print("[green]✓ Unknown tool handled gracefully[/green]")
    console.print(f"[bold]Error:[/bold] {result.error}")


def test_get_tools_by_category():
    """Test get_tools_by_category() function."""
    console.print("\n[bold cyan]Testing get_tools_by_category()[/bold cyan]")

    # Test extraction tools
    extraction = get_tools_by_category("extraction")
    assert len(extraction) == len(EXTRACTION_TOOLS)
    assert all(t['name'] in EXTRACTION_TOOLS for t in extraction)
    console.print(f"[green]✓ Extraction category: {len(extraction)} tools[/green]")

    # Test validation tools
    validation = get_tools_by_category("validation")
    assert len(validation) == len(VALIDATION_TOOLS)
    assert all(t['name'] in VALIDATION_TOOLS for t in validation)
    console.print(f"[green]✓ Validation category: {len(validation)} tools[/green]")

    # Test database tools
    database = get_tools_by_category("database")
    assert len(database) == len(DATABASE_TOOLS)
    assert all(t['name'] in DATABASE_TOOLS for t in database)
    console.print(f"[green]✓ Database category: {len(database)} tools[/green]")

    # Test invalid category
    try:
        get_tools_by_category("invalid")
        console.print("[red]✗ Should have raised ValueError[/red]")
        assert False
    except ValueError as e:
        console.print(f"[green]✓ Raises ValueError for invalid category[/green]")


def test_tool_categories():
    """Test tool category constants."""
    console.print("\n[bold cyan]Testing Tool Category Constants[/bold cyan]")

    # Verify categories are lists
    assert isinstance(EXTRACTION_TOOLS, list)
    assert isinstance(VALIDATION_TOOLS, list)
    assert isinstance(DATABASE_TOOLS, list)

    # Verify all tools are categorized
    all_categorized = set(EXTRACTION_TOOLS + VALIDATION_TOOLS + DATABASE_TOOLS)
    all_registered = set(TOOL_REGISTRY.keys())

    assert all_categorized == all_registered, "All tools should be categorized"

    console.print("[green]✓ All tools are properly categorized[/green]")

    # Show category breakdown
    table = Table(title="Tool Categories")
    table.add_column("Category", style="cyan")
    table.add_column("Tools", style="white")
    table.add_column("Count", style="green")

    table.add_row("Extraction", ", ".join(EXTRACTION_TOOLS), str(len(EXTRACTION_TOOLS)))
    table.add_row("Validation", ", ".join(VALIDATION_TOOLS), str(len(VALIDATION_TOOLS)))
    table.add_row("Database", ", ".join(DATABASE_TOOLS), str(len(DATABASE_TOOLS)))

    console.print(table)


def test_usage_example():
    """Show usage examples."""
    console.print("\n[bold cyan]Usage Examples[/bold cyan]")

    example1 = '''
# Example 1: Get all tools for Claude
from tools import get_all_tools

tools = get_all_tools()
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    tools=tools,  # All 5 tools
    messages=[...]
)
'''

    example2 = '''
# Example 2: Get tools by category
from tools import get_tools_by_category

validation_tools = get_tools_by_category("validation")
response = client.messages.create(
    tools=validation_tools,  # Only validation tools
    messages=[...]
)
'''

    example3 = '''
# Example 3: Execute tool from Claude's response
from tools import execute_tool

for block in response.content:
    if block.type == "tool_use":
        result = execute_tool(block.name, block.input)
        if result.success:
            print(f"✓ {block.name} succeeded")
        else:
            print(f"✗ {block.name} failed: {result.error}")
'''

    console.print(Panel(example1, title="Example 1: All Tools", border_style="cyan"))
    console.print(Panel(example2, title="Example 2: By Category", border_style="cyan"))
    console.print(Panel(example3, title="Example 3: Execute Tool", border_style="cyan"))


def main():
    """Run all tests."""
    console.print("[bold magenta]Tool Registry - Test Suite[/bold magenta]")

    try:
        test_tool_registry_structure()
        test_tool_executors_structure()
        test_get_all_tools()
        test_get_tool_names()
        test_get_tool_definition()
        test_execute_tool_success()
        test_execute_tool_validation_error()
        test_execute_tool_unknown()
        test_get_tools_by_category()
        test_tool_categories()
        test_usage_example()

        console.print("\n[bold green]✓ All tool registry tests passed![/bold green]")
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
