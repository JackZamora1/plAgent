#!/usr/bin/env python3
"""Test Anthropic tool integration."""
from tools.extraction_tools import (
    to_anthropic_tool,
    SAVE_OFFICER_BIO_TOOL,
    execute_save_officer_bio
)
from schema import OfficerBio, Promotion
from rich.console import Console
from rich.panel import Panel
from rich.json import JSON
import json

console = Console()


def test_to_anthropic_tool():
    """Test Pydantic to Anthropic tool schema conversion."""
    console.print("\n[bold cyan]Testing to_anthropic_tool()[/bold cyan]")

    schema = to_anthropic_tool(OfficerBio)

    # Verify schema structure
    assert schema['type'] == 'object', "Schema type should be 'object'"
    assert 'properties' in schema, "Schema should have 'properties'"
    assert 'required' in schema, "Schema should have 'required'"

    # Verify required fields
    assert 'name' in schema['required'], "'name' should be required"
    assert 'source_url' in schema['required'], "'source_url' should be required"

    # Verify property types
    props = schema['properties']
    assert props['name']['type'] == 'string', "'name' should be string"
    assert props['promotions']['type'] == 'array', "'promotions' should be array"

    # Verify nested Promotion schema
    promotion_items = props['promotions']['items']
    assert promotion_items['type'] == 'object', "Promotion items should be objects"
    assert 'rank' in promotion_items['properties'], "Promotion should have 'rank'"
    assert 'rank' in promotion_items['required'], "'rank' should be required in Promotion"

    console.print("[green]✓ Schema structure validated[/green]")
    console.print("\n[bold]Generated Schema (sample):[/bold]")
    console.print(Panel(
        JSON(json.dumps({
            'name': props['name'],
            'promotions': props['promotions'],
            'confidence_score': props.get('confidence_score')
        }, indent=2)),
        title="Sample Schema Fields"
    ))


def test_save_officer_bio_tool_definition():
    """Test SAVE_OFFICER_BIO_TOOL definition."""
    console.print("\n[bold cyan]Testing SAVE_OFFICER_BIO_TOOL Definition[/bold cyan]")

    # Verify tool structure
    assert 'name' in SAVE_OFFICER_BIO_TOOL, "Tool should have 'name'"
    assert 'description' in SAVE_OFFICER_BIO_TOOL, "Tool should have 'description'"
    assert 'input_schema' in SAVE_OFFICER_BIO_TOOL, "Tool should have 'input_schema'"

    # Verify tool name
    assert SAVE_OFFICER_BIO_TOOL['name'] == 'save_officer_bio', "Tool name should be 'save_officer_bio'"

    # Verify description is informative
    description = SAVE_OFFICER_BIO_TOOL['description']
    assert len(description) > 50, "Description should be detailed"
    assert 'PLA officer' in description, "Description should mention PLA officer"

    # Verify input schema
    schema = SAVE_OFFICER_BIO_TOOL['input_schema']
    assert schema['type'] == 'object', "Input schema type should be 'object'"
    assert 'name' in schema['required'], "'name' should be required"

    console.print("[green]✓ Tool definition validated[/green]")
    console.print(f"\n[bold]Tool Name:[/bold] {SAVE_OFFICER_BIO_TOOL['name']}")
    console.print(f"[bold]Description:[/bold] {description[:100]}...")
    console.print(f"[bold]Required Fields:[/bold] {schema['required']}")


def test_execute_save_officer_bio_success():
    """Test successful execution of save_officer_bio."""
    console.print("\n[bold cyan]Testing execute_save_officer_bio() - Success Case[/bold cyan]")

    # Valid input
    tool_input = {
        "name": "林炳尧",
        "source_url": "https://www.news.cn/example/c.html",
        "pinyin_name": "Lin Bingyao",
        "hometown": "福建晋江",
        "birth_date": "1943",
        "enlistment_date": "1961",
        "party_membership_date": "1964",
        "death_date": "2025-08-18",
        "congress_participation": ["第十五次全国代表大会"],
        "cppcc_participation": ["第十一届全国委员会委员"],
        "promotions": [
            {"rank": "少将", "date": "1995"},
            {"rank": "中将", "date": "2002"}
        ],
        "notable_positions": ["原南京军区副司令员"],
        "confidence_score": 0.95,
        "extraction_notes": "High confidence extraction from official obituary"
    }

    result = execute_save_officer_bio(tool_input)

    # Verify result
    assert result.success, "Execution should succeed"
    assert result.tool_name == "save_officer_bio", "Tool name should be 'save_officer_bio'"
    assert result.data is not None, "Data should be present"
    assert 'officer_bio' in result.data, "Result should contain 'officer_bio'"
    assert result.error is None, "Error should be None on success"

    console.print("[green]✓ Successful execution validated[/green]")
    console.print("\n[bold]Result Data:[/bold]")
    console.print(Panel(
        JSON(json.dumps(result.data, ensure_ascii=False, indent=2)),
        title="Execution Result"
    ))


def test_execute_save_officer_bio_validation_error():
    """Test validation error handling."""
    console.print("\n[bold cyan]Testing execute_save_officer_bio() - Validation Error[/bold cyan]")

    # Invalid input - missing required field 'name'
    invalid_input = {
        "source_url": "https://www.news.cn/example/c.html",
        # Missing 'name' field!
        "promotions": [{"rank": "少将"}]
    }

    result = execute_save_officer_bio(invalid_input)

    # Verify error handling
    assert not result.success, "Execution should fail"
    assert result.error is not None, "Error message should be present"
    assert 'name' in result.error.lower(), "Error should mention missing 'name' field"

    console.print("[green]✓ Validation error handling validated[/green]")
    console.print(f"\n[bold]Error Message:[/bold]")
    console.print(Panel(result.error, title="Validation Error", border_style="red"))


def test_execute_save_officer_bio_invalid_date():
    """Test date validation error."""
    console.print("\n[bold cyan]Testing execute_save_officer_bio() - Invalid Date[/bold cyan]")

    # Invalid input - bad date format
    invalid_input = {
        "name": "测试",
        "source_url": "https://example.com",
        "birth_date": "95-01-01",  # Invalid format!
    }

    result = execute_save_officer_bio(invalid_input)

    # Verify error handling
    assert not result.success, "Execution should fail"
    assert 'date' in result.error.lower() or 'format' in result.error.lower(), \
        "Error should mention date format issue"

    console.print("[green]✓ Date validation error handling validated[/green]")
    console.print(f"\n[bold]Error Message:[/bold]")
    console.print(Panel(result.error, title="Date Validation Error", border_style="red"))


def test_anthropic_api_format():
    """Test that tool definition works with Anthropic API format."""
    console.print("\n[bold cyan]Testing Anthropic API Compatibility[/bold cyan]")

    # Simulate how Claude API would receive this
    tools = [SAVE_OFFICER_BIO_TOOL]

    console.print("[green]✓ Tool definition is in correct format for Anthropic API[/green]")
    console.print("\n[bold]Tool Definition for Claude API:[/bold]")
    console.print(Panel(
        JSON(json.dumps(SAVE_OFFICER_BIO_TOOL, indent=2)),
        title="Anthropic Tool Schema",
        expand=False
    ))

    # Verify it can be JSON serialized (required for API)
    try:
        json_str = json.dumps(tools)
        console.print(f"\n[green]✓ Tool definition is JSON serializable ({len(json_str)} chars)[/green]")
    except Exception as e:
        console.print(f"[red]✗ JSON serialization failed: {e}[/red]")
        raise


def test_nested_model_handling():
    """Test handling of nested Promotion model."""
    console.print("\n[bold cyan]Testing Nested Model (Promotion) Handling[/bold cyan]")

    schema = to_anthropic_tool(OfficerBio)
    promotion_schema = schema['properties']['promotions']['items']

    # Verify Promotion schema is properly nested
    assert 'properties' in promotion_schema, "Promotion should have properties"
    assert 'rank' in promotion_schema['properties'], "Promotion should have 'rank' property"
    assert 'date' in promotion_schema['properties'], "Promotion should have 'date' property"
    assert 'unit' in promotion_schema['properties'], "Promotion should have 'unit' property"

    # Verify required fields
    assert 'rank' in promotion_schema['required'], "'rank' should be required in Promotion"

    console.print("[green]✓ Nested Promotion model properly handled[/green]")
    console.print("\n[bold]Promotion Schema:[/bold]")
    console.print(Panel(
        JSON(json.dumps(promotion_schema, indent=2)),
        title="Nested Promotion Schema"
    ))


def main():
    """Run all tests."""
    console.print("[bold magenta]Anthropic Tool Integration - Test Suite[/bold magenta]")

    try:
        test_to_anthropic_tool()
        test_save_officer_bio_tool_definition()
        test_execute_save_officer_bio_success()
        test_execute_save_officer_bio_validation_error()
        test_execute_save_officer_bio_invalid_date()
        test_nested_model_handling()
        test_anthropic_api_format()

        console.print("\n[bold green]✓ All Anthropic tool tests passed![/bold green]")
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
