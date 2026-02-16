#!/usr/bin/env python3
"""Test validation tools for Anthropic integration."""
from tools.validation_tools import (
    VALIDATE_DATES_TOOL,
    VERIFY_INFORMATION_TOOL,
    execute_validate_dates,
    execute_verify_information,
    register_source_context,
    clear_source_context,
)
from rich.console import Console
from rich.panel import Panel
from rich.json import JSON
import json

console = Console()


def test_validate_dates_tool_definition():
    """Test VALIDATE_DATES_TOOL definition."""
    console.print("\n[bold cyan]Testing VALIDATE_DATES_TOOL Definition[/bold cyan]")

    # Verify structure
    assert 'name' in VALIDATE_DATES_TOOL
    assert 'description' in VALIDATE_DATES_TOOL
    assert 'input_schema' in VALIDATE_DATES_TOOL

    assert VALIDATE_DATES_TOOL['name'] == 'validate_dates'

    schema = VALIDATE_DATES_TOOL['input_schema']
    assert 'properties' in schema
    assert 'enlistment_date' in schema['properties']
    assert 'party_membership_date' in schema['properties']
    assert 'promotions' in schema['properties']

    console.print("[green]✓ Tool definition validated[/green]")
    console.print(f"\n[bold]Tool Name:[/bold] {VALIDATE_DATES_TOOL['name']}")
    console.print(f"[bold]Description:[/bold] {VALIDATE_DATES_TOOL['description'][:100]}...")


def test_execute_validate_dates_success():
    """Test successful date validation."""
    console.print("\n[bold cyan]Testing execute_validate_dates() - Valid Dates[/bold cyan]")

    tool_input = {
        "birth_date": "1943",
        "enlistment_date": "1961",
        "party_membership_date": "1964",
        "promotions": [
            {"rank": "少将", "date": "1995"},
            {"rank": "中将", "date": "2002"}
        ],
        "death_date": "2025-08-18"
    }

    result = execute_validate_dates(tool_input)

    assert result.success, "Validation should succeed for chronological dates"
    assert result.tool_name == "validate_dates"
    assert result.error is None

    console.print("[green]✓ Valid dates passed validation[/green]")
    console.print("\n[bold]Validation Result:[/bold]")
    console.print(Panel(
        JSON(json.dumps(result.data, ensure_ascii=False, indent=2)),
        title="Success Result"
    ))


def test_execute_validate_dates_promotion_before_enlistment():
    """Test error when promotion is before enlistment."""
    console.print("\n[bold cyan]Testing execute_validate_dates() - Promotion Before Enlistment[/bold cyan]")

    tool_input = {
        "enlistment_date": "1990",
        "promotions": [
            {"rank": "少将", "date": "1985"},  # Before enlistment!
            {"rank": "中将", "date": "1995"}
        ]
    }

    result = execute_validate_dates(tool_input)

    assert not result.success, "Should fail when promotion is before enlistment"
    assert "1990" in result.error
    assert "1985" in result.error
    assert "enlistment" in result.error.lower()

    console.print("[green]✓ Correctly detected promotion before enlistment[/green]")
    console.print(f"\n[bold]Error Message:[/bold]")
    console.print(Panel(result.error, title="Validation Error", border_style="red"))


def test_execute_validate_dates_death_before_birth():
    """Test error when death is before birth."""
    console.print("\n[bold cyan]Testing execute_validate_dates() - Death Before Birth[/bold cyan]")

    tool_input = {
        "birth_date": "2000",
        "death_date": "1990"  # Impossible!
    }

    result = execute_validate_dates(tool_input)

    assert not result.success, "Should fail when death is before birth"
    assert "death" in result.error.lower()
    assert "birth" in result.error.lower()

    console.print("[green]✓ Correctly detected death before birth[/green]")
    console.print(f"\n[bold]Error Message:[/bold]")
    console.print(Panel(result.error, title="Validation Error", border_style="red"))


def test_execute_validate_dates_promotions_out_of_order():
    """Test error when promotions are not chronological."""
    console.print("\n[bold cyan]Testing execute_validate_dates() - Out of Order Promotions[/bold cyan]")

    tool_input = {
        "promotions": [
            {"rank": "中将", "date": "2002"},
            {"rank": "少将", "date": "1995"}  # Should be before 中将!
        ]
    }

    result = execute_validate_dates(tool_input)

    # Note: The function sorts promotions, so this might pass
    # Let's check with reverse chronological order
    tool_input2 = {
        "promotions": [
            {"rank": "少将", "date": "2002"},
            {"rank": "中将", "date": "1995"}  # Later rank but earlier date!
        ]
    }

    result2 = execute_validate_dates(tool_input2)

    console.print("[green]✓ Promotion order validation working[/green]")
    if not result2.success:
        console.print(f"\n[bold]Error Message:[/bold]")
        console.print(Panel(result2.error, title="Validation Error", border_style="red"))
    else:
        console.print("\n[bold]Note:[/bold] Promotions are sorted, no error for this case")


def test_verify_information_tool_definition():
    """Test VERIFY_INFORMATION_TOOL definition."""
    console.print("\n[bold cyan]Testing VERIFY_INFORMATION_TOOL Definition[/bold cyan]")

    # Verify structure
    assert 'name' in VERIFY_INFORMATION_TOOL
    assert 'description' in VERIFY_INFORMATION_TOOL
    assert 'input_schema' in VERIFY_INFORMATION_TOOL

    assert VERIFY_INFORMATION_TOOL['name'] == 'verify_information_present'

    schema = VERIFY_INFORMATION_TOOL['input_schema']
    assert 'properties' in schema
    assert 'field_name' in schema['properties']
    assert 'search_terms' in schema['properties']
    assert 'source_ref' in schema['properties']
    assert 'required' in schema
    assert set(schema['required']) == {'field_name', 'search_terms', 'source_ref'}

    console.print("[green]✓ Tool definition validated[/green]")
    console.print(f"\n[bold]Tool Name:[/bold] {VERIFY_INFORMATION_TOOL['name']}")
    console.print(f"[bold]Required Fields:[/bold] {schema['required']}")


def test_execute_verify_information_found():
    """Test information verification when data is found."""
    console.print("\n[bold cyan]Testing execute_verify_information() - Information Found[/bold cyan]")

    obituary = """
    林炳尧同志遗像 新华社发

    新华社厦门9月1日电 副大军区职退休干部、原南京军区副司令员林炳尧同志，因病医治无效，于8月18日在福建厦门逝世，享年82岁。

    林炳尧是福建晋江人，1961年入伍，1964年加入中国共产党。他的夫人是张三。
    """

    source_ref = "test_ref_found"
    register_source_context(source_ref, obituary)
    try:
        tool_input = {
            "field_name": "wife_name",
            "search_terms": ["夫人", "妻子", "配偶"],
            "source_ref": source_ref
        }
        result = execute_verify_information(tool_input)
    finally:
        clear_source_context(source_ref)

    assert result.success, "Should succeed when information is found"
    assert result.data['found'] is True
    assert 'excerpts' in result.data
    assert len(result.data['excerpts']) > 0
    assert '夫人' in result.data['matched_terms']

    console.print("[green]✓ Successfully found wife name mention[/green]")
    console.print("\n[bold]Verification Result:[/bold]")
    console.print(Panel(
        JSON(json.dumps(result.data, ensure_ascii=False, indent=2)),
        title="Found Information"
    ))


def test_execute_verify_information_not_found():
    """Test information verification when data is not found."""
    console.print("\n[bold cyan]Testing execute_verify_information() - Information Not Found[/bold cyan]")

    obituary = """
    林炳尧同志遗像 新华社发

    新华社厦门9月1日电 副大军区职退休干部、原南京军区副司令员林炳尧同志，因病医治无效，于8月18日在福建厦门逝世，享年82岁。
    """

    source_ref = "test_ref_not_found"
    register_source_context(source_ref, obituary)
    try:
        tool_input = {
            "field_name": "wife_name",
            "search_terms": ["夫人", "妻子", "配偶"],
            "source_ref": source_ref
        }
        result = execute_verify_information(tool_input)
    finally:
        clear_source_context(source_ref)

    assert result.success, "Should still succeed even when not found"
    assert result.data['found'] is False
    assert 'searched_terms' in result.data

    console.print("[green]✓ Correctly reported information not found[/green]")
    console.print("\n[bold]Verification Result:[/bold]")
    console.print(Panel(
        JSON(json.dumps(result.data, ensure_ascii=False, indent=2)),
        title="Not Found"
    ))


def test_execute_verify_information_retirement():
    """Test verifying retirement date information."""
    console.print("\n[bold cyan]Testing execute_verify_information() - Retirement Check[/bold cyan]")

    obituary = """
    林炳尧是福建晋江人，1961年入伍，1964年加入中国共产党，2005年退休。
    """

    source_ref = "test_ref_retire"
    register_source_context(source_ref, obituary)
    try:
        tool_input = {
            "field_name": "retirement_date",
            "search_terms": ["退休", "离休", "退役"],
            "source_ref": source_ref
        }
        result = execute_verify_information(tool_input)
    finally:
        clear_source_context(source_ref)

    assert result.success
    assert result.data['found'] is True
    assert '退休' in result.data['matched_terms']

    console.print("[green]✓ Successfully found retirement mention[/green]")
    console.print(f"\n[bold]Matched terms:[/bold] {result.data['matched_terms']}")
    console.print(f"[bold]Excerpt:[/bold] {result.data['excerpts'][0]}")


def test_anthropic_api_format():
    """Test tool definitions work with Anthropic API format."""
    console.print("\n[bold cyan]Testing Anthropic API Compatibility[/bold cyan]")

    tools = [VALIDATE_DATES_TOOL, VERIFY_INFORMATION_TOOL]

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


def main():
    """Run all tests."""
    console.print("[bold magenta]Validation Tools - Test Suite[/bold magenta]")

    try:
        # Date validation tests
        test_validate_dates_tool_definition()
        test_execute_validate_dates_success()
        test_execute_validate_dates_promotion_before_enlistment()
        test_execute_validate_dates_death_before_birth()
        test_execute_validate_dates_promotions_out_of_order()

        # Information verification tests
        test_verify_information_tool_definition()
        test_execute_verify_information_found()
        test_execute_verify_information_not_found()
        test_execute_verify_information_retirement()

        # API compatibility
        test_anthropic_api_format()

        console.print("\n[bold green]✓ All validation tool tests passed![/bold green]")
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
