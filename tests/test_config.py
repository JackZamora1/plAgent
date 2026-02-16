#!/usr/bin/env python3
"""Test script for Pydantic-based configuration system."""
from config import CONFIG
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def test_config_instance():
    """Test the global CONFIG instance."""
    console.print("\n[bold cyan]Testing CONFIG instance (Pydantic BaseSettings)[/bold cyan]\n")

    # Display CONFIG attributes
    table = Table(title="CONFIG Instance Attributes")
    table.add_column("Attribute", style="cyan")
    table.add_column("Value", style="white")
    table.add_column("Type", style="dim")

    attributes = [
        ("ANTHROPIC_API_KEY", "***" if CONFIG.ANTHROPIC_API_KEY else "Not set", str),
        ("DATABASE_URL", "***" if CONFIG.DATABASE_URL else "Not set", str),
        ("DB_HOST", CONFIG.DB_HOST, str),
        ("DB_NAME", CONFIG.DB_NAME, str),
        ("DB_USER", CONFIG.DB_USER if CONFIG.DB_USER else "Not set", str),
        ("DB_PASSWORD", "***" if CONFIG.DB_PASSWORD else "Not set", str),
        ("DB_PORT", CONFIG.DB_PORT, int),
        ("MODEL_NAME", CONFIG.MODEL_NAME, str),
        ("LOG_LEVEL", CONFIG.LOG_LEVEL, str),
    ]

    for attr_name, value, expected_type in attributes:
        table.add_row(attr_name, str(value), expected_type.__name__)

    console.print(table)

    # Test methods
    console.print("\n[bold cyan]Testing CONFIG methods:[/bold cyan]\n")

    # Test get_db_connection_string
    try:
        conn_str = CONFIG.get_db_connection_string()
        # Mask password in connection string
        if CONFIG.DB_PASSWORD:
            masked_conn_str = conn_str.replace(CONFIG.DB_PASSWORD, "***")
        else:
            masked_conn_str = conn_str
        console.print(f"[green]✓ get_db_connection_string(): {masked_conn_str}[/green]")
    except Exception as e:
        console.print(f"[red]✗ get_db_connection_string() failed: {e}[/red]")

    # Test validate_db_credentials (non-required)
    try:
        CONFIG.validate_db_credentials(require_db=False)
        console.print("[green]✓ validate_db_credentials(require_db=False): Passed[/green]")
    except Exception as e:
        console.print(f"[yellow]⚠ validate_db_credentials(require_db=False): {e}[/yellow]")

    # Test validate_db_credentials (required)
    try:
        CONFIG.validate_db_credentials(require_db=True)
        console.print("[green]✓ validate_db_credentials(require_db=True): Database credentials present[/green]")
    except ValueError as e:
        console.print(f"[yellow]⚠ validate_db_credentials(require_db=True): {e}[/yellow]")


def test_pydantic_features():
    """Test Pydantic-specific features."""
    console.print("\n[bold cyan]Testing Pydantic Features[/bold cyan]\n")

    # Test model_dump
    config_dict = CONFIG.model_dump()
    console.print(f"[green]✓ model_dump() returns {len(config_dict)} fields[/green]")

    # Test model_dump_json
    config_json = CONFIG.model_dump_json(indent=2, exclude={'ANTHROPIC_API_KEY', 'DB_PASSWORD'})
    console.print("\n[bold]CONFIG as JSON (sensitive fields excluded):[/bold]")
    console.print(Panel(config_json, border_style="dim"))

    # Test field validation
    console.print(f"\n[bold]Field Types:[/bold]")
    console.print(f"  DB_PORT: {type(CONFIG.DB_PORT).__name__} = {CONFIG.DB_PORT}")
    console.print(f"  MODEL_NAME: {type(CONFIG.MODEL_NAME).__name__} = {CONFIG.MODEL_NAME}")


def main():
    """Run all tests."""
    console.print(Panel.fit(
        "[bold magenta]Configuration System Test Suite[/bold magenta]\n"
        "Testing Pydantic BaseSettings implementation",
        border_style="magenta"
    ))

    try:
        # Run tests
        test_config_instance()
        test_pydantic_features()

        console.print("\n[bold green]✓ All configuration tests completed![/bold green]\n")
        return 0

    except Exception as e:
        console.print(f"\n[bold red]✗ Test suite failed: {e}[/bold red]")
        import traceback
        console.print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit(main())
