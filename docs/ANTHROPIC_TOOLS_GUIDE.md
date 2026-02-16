# Anthropic Tools Guide

Current runtime is `single_pass` with local validation and gated verification.

## Tool Surface

The SDK registers tool definitions for validation and optional DB operations.

Core extraction path typically uses:

- `save_officer_bio`
- `validate_dates`
- `verify_information_present` (selectively)

Database-enabled runs may also use:

- `lookup_existing_officer`
- `lookup_unit_by_name`
- `save_to_database`

## Notes

- Verification uses `source_ref` context, not full source text payloads.
- Tool calls are tracked in extraction result output for observability.
