# Anthropic Tools Integration Guide

Guide for using the Anthropic tool integration in the PLA Agent SDK.

## Overview

The SDK provides seamless integration between Pydantic models and Anthropic's tool use API. This allows Claude to extract structured officer biographical data using typed tool calls.

---

## Components

### 1. `to_anthropic_tool(pydantic_model)`

Converts any Pydantic model to Anthropic's tool schema format.

**Features:**
- ✓ Handles nested models (e.g., `Promotion` inside `OfficerBio`)
- ✓ Preserves field descriptions
- ✓ Maps types correctly (string, number, array, object)
- ✓ Identifies required vs optional fields
- ✓ Resolves `$ref` references automatically

**Example:**
```python
from tools.extraction_tools import to_anthropic_tool
from schema import OfficerBio

schema = to_anthropic_tool(OfficerBio)

# Schema is ready for Anthropic API
print(schema['type'])  # "object"
print(schema['required'])  # ['name', 'source_url']
print(schema['properties']['name']['type'])  # "string"
```

---

### 2. `SAVE_OFFICER_BIO_TOOL`

Pre-configured tool definition for saving officer biographical data.

**Structure:**
```python
{
    "name": "save_officer_bio",
    "description": "Save extracted biographical information...",
    "input_schema": {
        "type": "object",
        "properties": { ... },
        "required": ["name", "source_url"]
    }
}
```

**Usage with Anthropic API:**
```python
from anthropic import Anthropic
from tools.extraction_tools import SAVE_OFFICER_BIO_TOOL

client = Anthropic(api_key="your-key")

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    tools=[SAVE_OFFICER_BIO_TOOL],
    messages=[{
        "role": "user",
        "content": "Extract officer info from this obituary: ..."
    }]
)

# Claude will use the tool when it has extracted all data
for block in response.content:
    if block.type == "tool_use" and block.name == "save_officer_bio":
        tool_input = block.input
        # Process the extracted data
```

---

### 3. `execute_save_officer_bio(tool_input)`

Validates and processes tool input from Claude.

**Parameters:**
- `tool_input`: Dictionary with officer data (from Claude's tool call)

**Returns:**
- `ToolResult` object with:
  - `success=True`: Validation passed, data in `result.data['officer_bio']`
  - `success=False`: Validation failed, errors in `result.error`

**Example:**
```python
from tools.extraction_tools import execute_save_officer_bio

# After Claude calls the tool
tool_input = {
    "name": "林炳尧",
    "source_url": "https://www.news.cn/example.html",
    "promotions": [
        {"rank": "少将", "date": "1995"},
        {"rank": "中将", "date": "2002"}
    ],
    "confidence_score": 0.95
}

result = execute_save_officer_bio(tool_input)

if result.success:
    officer_bio = result.data['officer_bio']
    print(f"Extracted: {officer_bio['name']}")
    print(f"Confidence: {officer_bio['confidence_score']}")
else:
    print(f"Validation error: {result.error}")
```

---

## Complete Agent Example

```python
from anthropic import Anthropic
from tools.extraction_tools import SAVE_OFFICER_BIO_TOOL, execute_save_officer_bio
from tools.extraction_tools import extract_text_from_file

# Initialize client
client = Anthropic(api_key="your-key")

# Load source text
source_text = extract_text_from_file("data/test_obituary.txt")

# Create extraction prompt
prompt = f"""Extract biographical information about the PLA officer from this source.

Source text:
{source_text}

Use the save_officer_bio tool to save the extracted information. Only call the tool once you have extracted all available data."""

# Call Claude with tool
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    tools=[SAVE_OFFICER_BIO_TOOL],
    messages=[{"role": "user", "content": prompt}]
)

# Process response
for block in response.content:
    if block.type == "tool_use":
        if block.name == "save_officer_bio":
            # Validate and process the extraction
            result = execute_save_officer_bio(block.input)

            if result.success:
                officer_data = result.data['officer_bio']

                # Save to file
                import json
                output_file = f"output/{officer_data['name']}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(officer_data, f, ensure_ascii=False, indent=2)

                print(f"✓ Saved officer data to {output_file}")
                print(f"  Confidence: {officer_data['confidence_score']}")
            else:
                print(f"✗ Validation failed: {result.error}")
```

---

## Tool Input Schema

The `save_officer_bio` tool accepts the following fields:

### Required Fields
- `name` (string): Chinese name of the officer
- `source_url` (string): Source URL of the obituary

### Optional Identity Fields
- `pinyin_name` (string): Romanized name
- `hometown` (string): Birthplace
- `birth_date` (string): YYYY or YYYY-MM-DD format

### Optional Service Dates
- `enlistment_date` (string): Military join date
- `party_membership_date` (string): CCP join date
- `retirement_date` (string): Retirement date
- `death_date` (string): Date of death

### Optional Political Participation
- `congress_participation` (array of strings): CCP Congress participations
- `cppcc_participation` (array of strings): CPPCC participations

### Optional Career Information
- `promotions` (array of objects): Military promotions
  - `rank` (string, required): Military rank
  - `date` (string, optional): Promotion date
  - `unit` (string, optional): Military unit
- `notable_positions` (array of strings): Key positions
- `awards` (array of strings): Military honors

### Optional Control Variables
- `wife_name` (string): Spouse name

### Optional Metadata
- `confidence_score` (number): 0.0-1.0 confidence
- `extraction_notes` (string): Agent's reasoning

---

## Tool Schema Generation

Create custom tools from your Pydantic models:

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from tools.extraction_tools import to_anthropic_tool

# Define your model
class CustomModel(BaseModel):
    name: str = Field(description="Person's name")
    age: Optional[int] = Field(None, description="Age in years")
    tags: List[str] = Field(default_factory=list)

# Convert to tool schema
custom_tool = {
    "name": "save_custom_data",
    "description": "Save custom data",
    "input_schema": to_anthropic_tool(CustomModel)
}

# Use with Claude
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    tools=[custom_tool],
    messages=[...]
)
```

---

## Validation and Error Handling

The SDK provides comprehensive validation:

### Field Type Validation
```python
# Wrong type for confidence_score
result = execute_save_officer_bio({
    "name": "测试",
    "source_url": "https://example.com",
    "confidence_score": "high"  # Should be float!
})

print(result.error)
# "Validation failed:
#  confidence_score: Input should be a valid number..."
```

### Date Format Validation
```python
# Invalid date format
result = execute_save_officer_bio({
    "name": "测试",
    "source_url": "https://example.com",
    "birth_date": "95-01-01"  # Wrong format!
})

print(result.error)
# "Validation failed:
#  birth_date: Value error, Date must be in YYYY or YYYY-MM-DD format..."
```

### Logical Date Validation
```python
# Death before birth
result = execute_save_officer_bio({
    "name": "测试",
    "source_url": "https://example.com",
    "birth_date": "2000",
    "death_date": "1990"  # Impossible!
})

print(result.error)
# "Validation failed:
#  Value error, Death date cannot be before birth date"
```

---

## Best Practices

### 1. Prompt Engineering

Guide Claude to use the tool correctly:

```python
prompt = """Extract biographical data from this obituary.

Guidelines:
- Set confidence_score based on clarity of information (0.0-1.0)
- Use YYYY or YYYY-MM-DD format for all dates
- Include extraction_notes to explain uncertainties
- Only call save_officer_bio once you have all available data

Obituary: {text}"""
```

### 2. Error Recovery

Handle validation errors gracefully:

```python
result = execute_save_officer_bio(tool_input)

if not result.success:
    # Log the error
    logger.error(f"Validation failed: {result.error}")

    # Optionally retry with Claude
    retry_prompt = f"""The previous extraction had errors:
    {result.error}

    Please fix these issues and call the tool again."""
```

### 3. Multi-Turn Conversations

Support iterative extraction:

```python
messages = [{"role": "user", "content": initial_prompt}]

while True:
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        tools=[SAVE_OFFICER_BIO_TOOL],
        messages=messages
    )

    # Check for tool use
    tool_used = False
    for block in response.content:
        if block.type == "tool_use":
            tool_used = True
            result = execute_save_officer_bio(block.input)

            # Add tool result to conversation
            messages.append({
                "role": "assistant",
                "content": response.content
            })
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result.to_dict())
                }]
            })

            if result.success:
                # Success! Break the loop
                return result.data['officer_bio']

    if not tool_used:
        break
```

---

## Testing

Run the test suite:

```bash
python test_anthropic_tools.py
```

Tests cover:
- ✓ Schema conversion with nested models
- ✓ Tool definition structure
- ✓ Successful extraction
- ✓ Validation error handling
- ✓ Date format validation
- ✓ Anthropic API compatibility

---

## Troubleshooting

### Issue: `$ref` not resolved in schema
**Solution:** The `to_anthropic_tool()` function automatically resolves all `$ref` references. Ensure you're using the latest version.

### Issue: Validation fails with unclear error
**Solution:** Check `result.data['errors']` for detailed field-level errors:
```python
if not result.success:
    for error in result.data.get('errors', []):
        print(error)
```

### Issue: Claude doesn't use the tool
**Solution:** Make your prompt more explicit:
```python
prompt = "... Use the save_officer_bio tool to save this data."
```

---

## Schema Output Example

```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "Chinese name of the officer"
    },
    "promotions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "rank": {"type": "string"},
          "date": {"type": "string"},
          "unit": {"type": "string"}
        },
        "required": ["rank"]
      }
    },
    "confidence_score": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
    }
  },
  "required": ["name", "source_url"]
}
```

This schema is automatically generated from the Pydantic models and is fully compatible with Anthropic's API.
