# Tool Registry Guide

The tool registry centralizes tool definitions and executors used by the SDK.

## Core Registry Concepts

- `TOOL_REGISTRY`: tool schemas for Anthropic tool-use interface
- `TOOL_EXECUTORS`: Python execution handlers for each tool
- `execute_tool(name, input)`: dispatch + standardized error handling

## Tool Groups

- Extraction: `save_officer_bio`
- Validation: `validate_dates`, `verify_information_present`
- Database: `lookup_existing_officer`, `lookup_unit_by_name`, `save_to_database`

## Typical Usage

```python
from tools import get_all_tools, execute_tool

tools = get_all_tools()
result = execute_tool("validate_dates", {"birth_date": "1943"})
```

## Design Notes

- Unknown tool names return structured `ToolResult` errors.
- Execution is logged with timing and success/failure.
- Registry enables consistent behavior across CLI, SDK, and tests.

## When to Update This Layer

- adding/removing tool schemas
- changing tool input contracts
- modifying execution dispatch behavior

## Related Docs

- `docs/ANTHROPIC_TOOLS_GUIDE.md`
- `docs/VALIDATION_TOOLS_GUIDE.md`
- `docs/DATABASE_TOOLS_GUIDE.md`
