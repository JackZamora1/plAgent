# ConversationPrinter Guide

Utility class for debugging and visualizing agent conversations and extraction results.

## Overview

The `ConversationPrinter` class provides two static methods for pretty-printing agent interactions using the Rich library:

1. **`print_conversation()`** - Visualize conversation flow
2. **`print_extraction_summary()`** - Display extraction results

---

## Features

### Color-Coded Output

- 🔵 **Blue** - User messages
- 🟢 **Green** - Assistant responses (text)
- 🟡 **Yellow** - Tool usage
- 🔵 **Cyan** - Tool results
- 🟣 **Magenta** - Section headers

### Automatic Formatting

- Indented tool uses for clarity
- Truncated long outputs (>200 chars for tool results, >300 for tool inputs)
- Turn numbering for conversation flow
- Null value highlighting (⚠ indicator)

---

## Method 1: `print_conversation()`

Pretty-print the entire conversation history.

### Signature

```python
@staticmethod
def print_conversation(messages: List[dict]):
```

### Parameters

- **messages** (`List[dict]`): Conversation messages from the agentic loop

### Usage

```python
from agent import ConversationPrinter

# After running extraction, print the conversation
messages = [
    {
        "role": "user",
        "content": "Extract biographical information from this obituary..."
    },
    {
        "role": "assistant",
        "content": [
            {"type": "text", "text": "I'll extract the information..."},
            {"type": "tool_use", "name": "lookup_existing_officer", "input": {...}}
        ]
    },
    {
        "role": "user",
        "content": [
            {"type": "tool_result", "content": '{"success": true, ...}'}
        ]
    }
]

ConversationPrinter.print_conversation(messages)
```

### Output Format

```
User (Turn 1):
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Extract biographical information from this obituary...       ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Assistant (Turn 2):
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ I'll extract the information...                             ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
  🔧 Using tool: lookup_existing_officer
    Input: {
      "name": "林炳尧"
    }

Tool Results (Turn 3):
  └─ Tool result:
    {"success": true, "found": false, "message": "Officer not found"}
```

### Handles Both Formats

The method works with:
- **Dict format** - Standard message structure
- **Anthropic API objects** - Direct response content blocks

---

## Method 2: `print_extraction_summary()`

Display a comprehensive summary of extraction results.

### Signature

```python
@staticmethod
def print_extraction_summary(result: AgentExtractionResult):
```

### Parameters

- **result** (`AgentExtractionResult`): The extraction result to summarize

### Usage

```python
from agent import PLAgentSDK, ConversationPrinter

# Run extraction
sdk = PLAgentSDK()
result = sdk.extract_bio_agentic(source_text, source_url, source_type="universal")

# Print summary
ConversationPrinter.print_extraction_summary(result)
```

### Output Sections

#### 1. Status

```
═══ Extraction Summary ═══

✓ Status: SUCCESS
```

Or for failures:

```
✗ Status: FAILED
Error: Maximum iterations (10) reached without completion
```

#### 2. Extracted Fields Table

Shows all fields with their values and status indicators:

```
Extracted Fields:

┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Field                   ┃ Value                          ┃ Status   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ name                    │ 林炳尧                         │ ✓        │
│ pinyin_name             │ null                           │ ⚠        │
│ hometown                │ 福建晋江                       │ ✓        │
│ birth_date              │ 1943                           │ ✓        │
│ death_date              │ 2023-01-15                     │ ✓        │
│ enlistment_date         │ 1961                           │ ✓        │
│ party_membership_date   │ 1964                           │ ✓        │
│ promotions              │ 2 item(s)                      │ ✓        │
│ notable_positions       │ 3 item(s)                      │ ✓        │
│ congress_participation  │ null                           │ ⚠        │
│ cppcc_participation     │ null                           │ ⚠        │
│ awards                  │ null                           │ ⚠        │
│ wife_name               │ null                           │ ⚠        │
│ ethnicity               │ null                           │ ⚠        │
│ retirement_date         │ null                           │ ⚠        │
└─────────────────────────┴────────────────────────────────┴──────────┘

Confidence Score: 0.87
```

**Status Indicators:**
- ✓ (green) - Field has value
- ⚠ (yellow) - Field is null (control variable)

#### 3. Performance Metrics

```
Performance Metrics:

Conversation Turns      4
Tool Calls              3
Input Tokens            2,345
Output Tokens           1,234
Total Tokens            3,579
Tool Success Rate       100.0%
```

#### 4. Tool Usage Breakdown

```
Tool Usage:

┏━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ #   ┃ Tool                         ┃ Status   ┃ Notes               ┃
┡━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ 1   │ lookup_existing_officer      │ ✓        │ New officer         │
│ 2   │ verify_information_present   │ ✓        │ Not found: wife_name│
│ 3   │ validate_dates               │ ✓        │ Dates validated     │
│ 4   │ save_officer_bio             │ ✓        │ Data saved          │
└─────┴──────────────────────────────┴──────────┴─────────────────────┘
```

---

## Complete Example

```python
#!/usr/bin/env python3
"""Example using ConversationPrinter for debugging."""
from agent import PLAgentSDK, ConversationPrinter
from tools.extraction_tools import extract_text_from_file
import logging

# Enable logging to see what's happening
logging.basicConfig(level=logging.INFO)

# Initialize SDK
sdk = PLAgentSDK(require_db=False)

# Load source text
source_text = extract_text_from_file("data/test_obituary.txt")

# Extract biography
result = sdk.extract_bio_agentic(
    source_text=source_text,
    source_url="https://www.news.cn/test/obituary.html",
    source_type="universal"
)

# Print comprehensive summary
ConversationPrinter.print_extraction_summary(result)

# Optionally: print the full conversation for debugging
# (Note: You'd need to capture messages from the agentic loop)
# ConversationPrinter.print_conversation(messages)
```

---

## Use Cases

### 1. Debugging Extraction Logic

Use `print_conversation()` to see exactly what Claude is doing:
- Which tools it chooses to use
- What inputs it provides to each tool
- How it responds to tool results

```python
# Add to PLAgentSDK.extract_bio_agentic() for debugging
ConversationPrinter.print_conversation(messages)
```

### 2. Quality Control

Use `print_extraction_summary()` to quickly review:
- Which fields are populated vs null
- Confidence scores
- Tool success rates

### 3. Performance Analysis

Check token usage and tool efficiency:
- How many conversation turns?
- How many tools called?
- What's the token cost?

### 4. Demo & Presentation

Use for demonstrations to show:
- Agentic behavior in action
- Tool use patterns
- Data quality and completeness

---

## Integration with Existing Code

### Replace existing display functions

In `demo_agentic_extraction.py`, you can replace the `display_result_summary()` function:

```python
# Old way
display_result_summary(result)

# New way (simpler)
from agent import ConversationPrinter
ConversationPrinter.print_extraction_summary(result)
```

### Add to PLAgentSDK for verbose mode

```python
class PLAgentSDK:
    def __init__(self, require_db: bool = False, verbose: bool = False):
        # ... existing code ...
        self.verbose = verbose

    def extract_bio_agentic(self, source_text: str, source_url: str, source_type: str = "universal"):
        # ... existing extraction code ...

        # At the end
        if self.verbose:
            ConversationPrinter.print_conversation(messages)

        return result
```

---

## Tips

### Truncation

Long outputs are automatically truncated:
- Tool results: 200 characters
- Tool inputs: 300 characters

To see full content, modify the limits in the source code or use JSON pretty-printing.

### Control Variables

Null fields are highlighted with ⚠ to distinguish between:
- **Populated fields** (✓) - Information was found
- **Control variables** (⚠) - Intentionally null (not mentioned in obituary)

This helps verify that the agent isn't hallucinating data.

### Color Customization

The Rich library colors can be customized by modifying the style strings:
- `[bold blue]` - User messages
- `[bold green]` - Assistant messages
- `[yellow]` - Tool uses
- `[cyan]` - Tool results
- `[magenta]` - Headers

---

## Summary

The `ConversationPrinter` class provides two key utilities:

| Method | Purpose | Output |
|--------|---------|--------|
| `print_conversation()` | Debug agent behavior | Turn-by-turn conversation flow |
| `print_extraction_summary()` | Review extraction quality | Field table, metrics, tool usage |

Both methods use the Rich library for beautiful, color-coded terminal output that makes debugging and quality control much easier!
