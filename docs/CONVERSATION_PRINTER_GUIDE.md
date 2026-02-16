# ConversationPrinter Guide

Utilities for inspecting extraction behavior and summarizing results.

## Overview

`ConversationPrinter` provides:

- `print_conversation(messages)`
- `print_extraction_summary(result)`

These are useful for debugging, QA review, and demos.

## Typical Usage

```python
from agent import PLAgentSDK, ConversationPrinter

sdk = PLAgentSDK(require_db=False)
result = sdk.extract_bio_agentic(source_text=source_text, source_url=source_url)

ConversationPrinter.print_extraction_summary(result)

# Optional: if you captured raw messages
# ConversationPrinter.print_conversation(messages)
```

## What Summary Output Shows

- extraction status
- field-level population overview
- confidence score
- token and tool-call metrics
- tool-by-tool results

## Debugging Tips

- Use summary output first to triage quickly.
- Use full conversation output when tool ordering or payload shape is unclear.
- Compare summaries across runs when prompt/config changes are introduced.

## Integration Pattern

```python
if verbose:
    ConversationPrinter.print_extraction_summary(result)
```

Keep this in CLI/debug scripts rather than core extraction logic.
