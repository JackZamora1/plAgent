# Validation Tools Guide

Validation tools enforce extraction quality in the single-pass pipeline.

## Available Tools

- `save_officer_bio` (schema/type validation path)
- `validate_dates` (chronology checks)
- `verify_information_present` (source evidence checks)

## Current Verification Model

- Runtime mode is single-pass.
- Verification uses `source_ref` (registered source context), not raw full-text payloads.
- Verification is selective (usually rare/suspicious fields).

## `validate_dates`

Checks:

- birth before enlistment/promotions/death
- enlistment before promotions
- promotions in chronological order
- death after major life dates

Example:

```python
from tools import execute_validate_dates

result = execute_validate_dates({
    "birth_date": "1943",
    "enlistment_date": "1961",
    "promotions": [{"rank": "少将", "date": "1995"}],
    "death_date": "2025-08-18",
})
```

## `verify_information_present`

Confirms whether a field is explicitly mentioned in source text.

Example:

```python
from tools.validation_tools import register_source_context, clear_source_context
from tools import execute_verify_information

source_ref = "src_demo_001"
register_source_context(source_ref, source_text)
try:
    result = execute_verify_information({
        "field_name": "wife_name",
        "search_terms": ["妻子", "夫人", "配偶"],
        "source_ref": source_ref,
    })
finally:
    clear_source_context(source_ref)
```

## Operational Guidance

- Keep search terms field-specific and conservative.
- Prefer null over speculation when verification cannot confirm presence.
- Review extraction notes for inferred/removed fields.

## Related Docs

- `docs/SCHEMA_GUIDE.md`
- `docs/WORKFLOW_GUIDE.md`
