# Tool Registry Guide

Guide for using the centralized tool registry to manage and dispatch Anthropic tools.

## Overview

The tool registry provides a centralized way to manage all Anthropic tools in the PLA Agent SDK. It simplifies adding new tools, dispatching to executors, and selecting tools by category.

---

## Core Components

### 1. TOOL_REGISTRY

Dictionary mapping tool names to their Anthropic API definitions.

```python
TOOL_REGISTRY = {
    "save_officer_bio": SAVE_OFFICER_BIO_TOOL,
    "validate_dates": VALIDATE_DATES_TOOL,
    "verify_information_present": VERIFY_INFORMATION_TOOL,
    "lookup_existing_officer": LOOKUP_OFFICER_TOOL,
    "lookup_unit_by_name": LOOKUP_UNIT_TOOL,
}
```

### 2. TOOL_EXECUTORS

Dictionary mapping tool names to their executor functions.

```python
TOOL_EXECUTORS = {
    "save_officer_bio": execute_save_officer_bio,
    "validate_dates": execute_validate_dates,
    "verify_information_present": execute_verify_information,
    "lookup_existing_officer": execute_lookup_officer,
    "lookup_unit_by_name": execute_lookup_unit,
}
```

### 3. Tool Categories

Tools are organized into three categories:

```python
EXTRACTION_TOOLS = ["save_officer_bio"]
VALIDATION_TOOLS = ["validate_dates", "verify_information_present"]
DATABASE_TOOLS = ["lookup_existing_officer", "lookup_unit_by_name"]
```

---

## Functions

### get_all_tools()

Get all tool definitions for the Anthropic API.

```python
from tools import get_all_tools
from anthropic import Anthropic

client = Anthropic(api_key="your-key")
tools = get_all_tools()

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    tools=tools,  # All 5 tools available
    messages=[{
        "role": "user",
        "content": "Extract officer bio from this obituary..."
    }]
)
```

**Returns:**
```python
[
    {
        "name": "save_officer_bio",
        "description": "...",
        "input_schema": {...}
    },
    # ... 4 more tools
]
```

---

### execute_tool()

Execute a tool by name with automatic dispatching and logging.

```python
from tools import execute_tool

# From Claude's response
for block in response.content:
    if block.type == "tool_use":
        # Automatically dispatch to correct executor
        result = execute_tool(block.name, block.input)

        if result.success:
            print(f"✓ {block.name} succeeded")
            # Use result.data
        else:
            print(f"✗ {block.name} failed: {result.error}")
```

**Features:**
- ✓ Automatic dispatching to correct executor
- ✓ Logging of execution time and status
- ✓ Graceful handling of unknown tools
- ✓ Returns ToolResult even on errors

**Error Handling:**
```python
result = execute_tool("nonexistent_tool", {})

if not result.success:
    print(result.error)
    # "Unknown tool: nonexistent_tool. Available tools: [...]"
```

---

### get_tool_names()

Get list of all registered tool names.

```python
from tools import get_tool_names

names = get_tool_names()
print(names)
# ['save_officer_bio', 'validate_dates', 'verify_information_present',
#  'lookup_existing_officer', 'lookup_unit_by_name']
```

---

### get_tool_definition()

Get the definition for a specific tool.

```python
from tools import get_tool_definition

tool_def = get_tool_definition("validate_dates")
print(tool_def['name'])         # "validate_dates"
print(tool_def['description'])  # "Check if extracted dates..."
print(tool_def['input_schema']) # {...}
```

---

### get_tools_by_category()

Get tool definitions for a specific category.

```python
from tools import get_tools_by_category

# Get only validation tools
validation_tools = get_tools_by_category("validation")

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    tools=validation_tools,  # Only 2 validation tools
    messages=[...]
)
```

**Categories:**
- `"extraction"` - Data extraction tools (1 tool)
- `"validation"` - Data validation tools (2 tools)
- `"database"` - Database lookup tools (2 tools)

---

## Complete Example

Using the tool registry for a full extraction workflow:

```python
from anthropic import Anthropic
from tools import get_all_tools, execute_tool

client = Anthropic(api_key="your-key")

# Get all tools
tools = get_all_tools()

# Initial message
messages = [{
    "role": "user",
    "content": f"""Extract officer bio from this source.

Process:
1. Check if officer exists (lookup_existing_officer)
2. Verify uncertain fields (verify_information_present)
3. Validate dates (validate_dates)
4. Save data (save_officer_bio)

Source text:
{source_text}"""
}]

# Loop for multi-turn conversation
while True:
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        tools=tools,
        messages=messages
    )

    # Process tool uses
    tool_results = []
    for block in response.content:
        if block.type == "tool_use":
            # Execute tool using registry
            result = execute_tool(block.name, block.input)

            # Collect for response
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result.model_dump_json()
            })

            # Handle specific tools
            if block.name == "save_officer_bio" and result.success:
                officer = result.data['officer_bio']
                print(f"✓ Saved: {officer['name']}")
                return officer  # Done!

    # If no tools, we're done
    if not tool_results:
        break

    # Continue conversation
    messages.append({"role": "assistant", "content": response.content})
    messages.append({"role": "user", "content": tool_results})
```

---

## Adding New Tools

To add a new tool to the registry:

### Step 1: Create the Tool

In the appropriate file (e.g., `tools/validation_tools.py`):

```python
# Tool definition
MY_NEW_TOOL = {
    "name": "my_new_tool",
    "description": "Description of what it does",
    "input_schema": {
        "type": "object",
        "properties": {
            "param1": {"type": "string"},
        },
        "required": ["param1"]
    }
}

# Executor function
def execute_my_new_tool(tool_input: Dict[str, Any]) -> ToolResult:
    """Execute my new tool."""
    try:
        # Tool logic here
        return ToolResult(
            tool_name="my_new_tool",
            success=True,
            data={"result": "..."}
        )
    except Exception as e:
        return ToolResult(
            tool_name="my_new_tool",
            success=False,
            error=str(e)
        )
```

### Step 2: Register the Tool

In `tools/__init__.py`:

```python
# Import
from .validation_tools import MY_NEW_TOOL, execute_my_new_tool

# Add to registry
TOOL_REGISTRY["my_new_tool"] = MY_NEW_TOOL
TOOL_EXECUTORS["my_new_tool"] = execute_my_new_tool

# Add to category
VALIDATION_TOOLS.append("my_new_tool")
```

**That's it!** The tool is now available through:
- `get_all_tools()` - Includes your new tool
- `execute_tool("my_new_tool", {...})` - Dispatches to your executor
- `get_tools_by_category("validation")` - Includes your new tool

---

## Logging

The `execute_tool()` function automatically logs:

```python
import logging

# Set up logging to see tool execution
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Now tool executions are logged
result = execute_tool("validate_dates", {...})
# INFO - tools - Executing tool: validate_dates
# INFO - tools - Tool 'validate_dates' executed in 0.03s - Success: True
```

**Log Levels:**
- `INFO` - Tool execution start and completion
- `DEBUG` - Tool input details
- `WARNING` - Tool execution failures
- `ERROR` - Unexpected exceptions

---

## Tool Selection Strategies

### Strategy 1: All Tools

Give Claude access to all tools:

```python
tools = get_all_tools()
```

**Pros:**
- Maximum flexibility
- Claude can use any tool as needed

**Cons:**
- More tokens in prompt
- Claude might use unexpected tools

---

### Strategy 2: By Category

Give Claude only relevant tools:

```python
# For validation only
tools = get_tools_by_category("validation")

# For database lookups only
tools = get_tools_by_category("database")
```

**Pros:**
- Focused tool set
- Fewer tokens
- More predictable behavior

**Cons:**
- Less flexibility
- Need to know which tools are needed upfront

---

### Strategy 3: Selective

Manually select specific tools:

```python
from tools import TOOL_REGISTRY

tools = [
    TOOL_REGISTRY["lookup_existing_officer"],
    TOOL_REGISTRY["save_officer_bio"]
]
```

**Pros:**
- Maximum control
- Minimal tokens
- Very predictable

**Cons:**
- Manual management
- Need to update when requirements change

---

### Strategy 4: Progressive

Start with limited tools, expand as needed:

```python
# Phase 1: Lookup only
tools = get_tools_by_category("database")
response = client.messages.create(tools=tools, messages=messages)

# Phase 2: Add validation
tools.extend(get_tools_by_category("validation"))
response = client.messages.create(tools=tools, messages=messages)

# Phase 3: Add extraction
tools.extend(get_tools_by_category("extraction"))
response = client.messages.create(tools=tools, messages=messages)
```

---

## Error Handling

The registry provides comprehensive error handling:

### Unknown Tool

```python
result = execute_tool("unknown", {})

if not result.success:
    print(result.error)
    # "Unknown tool: unknown. Available tools: [...]"
```

### Execution Exception

```python
# If executor raises exception
result = execute_tool("validate_dates", {"invalid": "input"})

if not result.success:
    print(result.error)
    # "Unexpected error during tool execution: ..."
```

### Validation Error

```python
# Tool-specific validation error
result = execute_tool("validate_dates", {
    "birth_date": "2000",
    "death_date": "1990"
})

if not result.success:
    print(result.error)
    # "Date inconsistencies found: ..."
```

---

## Testing

Run the tool registry test suite:

```bash
python test_tool_registry.py
```

Tests cover:
- ✓ Registry structure and completeness
- ✓ Executor function validity
- ✓ `get_all_tools()` functionality
- ✓ `execute_tool()` success cases
- ✓ `execute_tool()` error handling
- ✓ Unknown tool handling
- ✓ Tool categorization
- ✓ Category selection

---

## Best Practices

### 1. Always Use execute_tool()

Instead of calling executors directly:

```python
# ❌ Don't do this
from tools import execute_validate_dates
result = execute_validate_dates(input)

# ✓ Do this
from tools import execute_tool
result = execute_tool("validate_dates", input)
```

**Benefits:**
- Automatic logging
- Consistent error handling
- Easier to mock/test
- Future-proof

### 2. Use get_all_tools() for Flexibility

Unless you have specific constraints, use all tools:

```python
tools = get_all_tools()
```

This gives Claude maximum flexibility to choose the right tool.

### 3. Handle Errors Gracefully

Always check `result.success`:

```python
result = execute_tool(tool_name, tool_input)

if result.success:
    # Process result.data
    pass
else:
    # Handle result.error
    logger.warning(f"Tool failed: {result.error}")
```

### 4. Enable Logging

Enable logging to debug tool execution:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### 5. Keep Registry and Executors in Sync

When adding new tools, always update both:
- Add to `TOOL_REGISTRY`
- Add to `TOOL_EXECUTORS`
- Add to appropriate category list

---

## Summary

### Current Tools

| Tool Name | Category | Purpose |
|-----------|----------|---------|
| `save_officer_bio` | Extraction | Save extracted biographical data |
| `validate_dates` | Validation | Check chronological consistency |
| `verify_information_present` | Validation | Verify info exists in source |
| `lookup_existing_officer` | Database | Check for duplicate officers |
| `lookup_unit_by_name` | Database | Look up unit IDs |

### Key Functions

- `get_all_tools()` - Get all tool definitions
- `execute_tool()` - Execute tool with automatic dispatch
- `get_tool_names()` - List all tool names
- `get_tool_definition()` - Get single tool definition
- `get_tools_by_category()` - Get tools by category

### Benefits

- ✓ Centralized tool management
- ✓ Automatic dispatching
- ✓ Built-in logging
- ✓ Easy to add new tools
- ✓ Category-based selection
- ✓ Comprehensive error handling

The tool registry makes it simple to manage and use all Anthropic tools in the PLA Agent SDK!
