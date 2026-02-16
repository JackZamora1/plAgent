# Database Tools Guide

Database tools are optional helpers for deduplication, unit lookup, and persistence.

## Available Tools

- `lookup_existing_officer`
- `lookup_unit_by_name`
- `save_to_database`

## Typical Usage Pattern

1. Extract and validate officer data.
2. Optionally check duplicates with `lookup_existing_officer`.
3. Optionally resolve units with `lookup_unit_by_name`.
4. Persist final high-confidence result with `save_to_database`.

## Runtime Notes

- Database features require valid DB credentials in `.env`.
- If DB is unavailable, extraction still works; DB-related operations fail gracefully.
- Batch mode can save to DB when `--save-db` is enabled.

## Minimal Example

```python
from tools.database_tools import (
    execute_lookup_officer,
    execute_lookup_unit,
    save_officer_bio_to_database,
)

existing = execute_lookup_officer({"name": "林炳尧"})
unit = execute_lookup_unit({"unit_name": "南京军区"})
saved = save_officer_bio_to_database(officer_bio)
```

## Troubleshooting

- `connection refused`: PostgreSQL not running or wrong host/port
- `authentication failed`: wrong DB credentials
- `relation does not exist`: schema/table not initialized

## Related Docs

- `docs/CONFIGURATION_GUIDE.md`
- `docs/WORKFLOW_GUIDE.md`
- `docs/VALIDATION_TOOLS_GUIDE.md`
