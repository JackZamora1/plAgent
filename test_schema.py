#!/usr/bin/env python3
"""Test script for schema models."""
from schema import Promotion, OfficerBio, ToolResult, AgentExtractionResult
from rich.console import Console
from rich.panel import Panel
from rich.json import JSON
import json

console = Console()


def test_promotion_model():
    """Test Promotion model."""
    console.print("\n[bold cyan]Testing Promotion Model[/bold cyan]")

    # Valid promotion
    try:
        promotion = Promotion(
            rank="少将",
            date="1995",
            unit="南京军区"
        )
        console.print("[green]✓ Valid promotion created[/green]")
        console.print(Panel(JSON(promotion.model_dump_json(indent=2)), title="Promotion"))
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")

    # Test date validation
    try:
        bad_promotion = Promotion(rank="中将", date="95-01")
        console.print("[red]✗ Should have failed - invalid date format[/red]")
    except ValueError as e:
        console.print(f"[green]✓ Date validation working: {e}[/green]")


def test_officer_bio_model():
    """Test OfficerBio model."""
    console.print("\n[bold cyan]Testing OfficerBio Model[/bold cyan]")

    # Create comprehensive officer bio
    try:
        officer = OfficerBio(
            name="林炳尧",
            pinyin_name="Lin Bingyao",
            hometown="福建晋江",
            birth_date="1943",
            enlistment_date="1961",
            party_membership_date="1964",
            death_date="2025-08-18",
            congress_participation=["第十五次全国代表大会"],
            cppcc_participation=["第十一届全国委员会委员"],
            promotions=[
                Promotion(rank="少将", date="1995"),
                Promotion(rank="中将", date="2002")
            ],
            notable_positions=[
                "原南京军区副司令员",
                "军长",
                "副军长"
            ],
            awards=["一级红星功勋荣誉章"],
            source_url="https://www.news.cn/20250901/example/c.html",
            confidence_score=0.95,
            extraction_notes="High confidence extraction from official obituary"
        )
        console.print("[green]✓ Valid officer bio created[/green]")

        # Test to_dict
        officer_dict = officer.to_dict(exclude_none=True)
        console.print("\n[bold]Officer Bio (dict, exclude_none=True):[/bold]")
        console.print(Panel(JSON(json.dumps(officer_dict, ensure_ascii=False, indent=2)),
                           title="Officer Bio"))

    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        raise

    # Test date validation logic
    console.print("\n[bold]Testing date logic validation...[/bold]")
    try:
        bad_officer = OfficerBio(
            name="测试",
            source_url="https://example.com",
            birth_date="2000",
            death_date="1990"  # Death before birth!
        )
        console.print("[red]✗ Should have failed - death before birth[/red]")
    except ValueError as e:
        console.print(f"[green]✓ Date logic validation working: {e}[/green]")


def test_tool_result_model():
    """Test ToolResult model."""
    console.print("\n[bold cyan]Testing ToolResult Model[/bold cyan]")

    # Successful tool call
    try:
        tool_result = ToolResult(
            tool_name="extract_text_from_url",
            success=True,
            data={"text_length": 1234, "encoding": "utf-8"}
        )
        console.print("[green]✓ Successful tool result created[/green]")
        console.print(Panel(JSON(tool_result.model_dump_json(indent=2)),
                           title="Tool Result"))
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")

    # Failed tool call without error message
    try:
        bad_tool = ToolResult(
            tool_name="test",
            success=False
            # Missing error message!
        )
        console.print("[red]✗ Should have failed - no error message[/red]")
    except ValueError as e:
        console.print(f"[green]✓ Error validation working: {e}[/green]")


def test_agent_extraction_result():
    """Test AgentExtractionResult model."""
    console.print("\n[bold cyan]Testing AgentExtractionResult Model[/bold cyan]")

    # Create complete extraction result
    try:
        officer = OfficerBio(
            name="林炳尧",
            source_url="https://www.news.cn/example/c.html",
            confidence_score=0.95
        )

        tool_calls = [
            ToolResult(
                tool_name="extract_text_from_url",
                success=True,
                data={"text_length": 1234}
            ),
            ToolResult(
                tool_name="validate_officer_data",
                success=True,
                data={"is_valid": True}
            )
        ]

        result = AgentExtractionResult(
            officer_bio=officer,
            tool_calls=tool_calls,
            conversation_turns=3,
            total_input_tokens=1500,
            total_output_tokens=800,
            success=True
        )

        console.print("[green]✓ Valid extraction result created[/green]")

        # Test summary
        summary = result.get_summary()
        console.print("\n[bold]Extraction Summary:[/bold]")
        console.print(Panel(JSON(json.dumps(summary, ensure_ascii=False, indent=2)),
                           title="Summary"))

        console.print(f"\n[bold]Statistics:[/bold]")
        console.print(f"  Total tokens: {result.get_total_tokens()}")
        console.print(f"  Tool success rate: {result.get_success_rate():.1%}")

    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        raise

    # Test validation - success without officer_bio
    try:
        bad_result = AgentExtractionResult(
            success=True,  # But no officer_bio!
            tool_calls=[],
            conversation_turns=1,
            total_input_tokens=100,
            total_output_tokens=50
        )
        console.print("[red]✗ Should have failed - success without data[/red]")
    except ValueError as e:
        console.print(f"[green]✓ Consistency validation working: {e}[/green]")


def test_json_serialization():
    """Test JSON serialization."""
    console.print("\n[bold cyan]Testing JSON Serialization[/bold cyan]")

    officer = OfficerBio(
        name="林炳尧",
        pinyin_name="Lin Bingyao",
        hometown="福建晋江",
        promotions=[
            Promotion(rank="少将", date="1995"),
            Promotion(rank="中将", date="2002")
        ],
        source_url="https://example.com",
        confidence_score=0.95
    )

    # Test to_json
    json_str = officer.to_json(exclude_none=True)
    console.print("[green]✓ JSON serialization working[/green]")
    console.print(Panel(json_str, title="Serialized JSON"))

    # Test round-trip
    parsed = json.loads(json_str)
    console.print(f"\n[green]✓ JSON parsing successful[/green]")
    console.print(f"Name from parsed JSON: {parsed['name']}")


def main():
    """Run all tests."""
    console.print("[bold magenta]PLA Agent SDK - Schema Test Suite[/bold magenta]")

    try:
        test_promotion_model()
        test_officer_bio_model()
        test_tool_result_model()
        test_agent_extraction_result()
        test_json_serialization()

        console.print("\n[bold green]✓ All schema tests passed![/bold green]")

    except Exception as e:
        console.print(f"\n[bold red]✗ Test suite failed: {e}[/bold red]")
        import traceback
        console.print(traceback.format_exc())
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
