# Configuration Guide

Configuration uses Pydantic `BaseSettings` and loads values from `.env`.

## Quick Start

```bash
# Required
ANTHROPIC_API_KEY=your_api_key_here

# Optional database
DATABASE_URL=postgresql://user:password@localhost:5432/pla_db
# or DB_HOST / DB_NAME / DB_USER / DB_PASSWORD / DB_PORT

# Optional runtime tuning
MODEL_NAME=claude-sonnet-4-6
LOG_LEVEL=INFO
MAX_VERIFY_CALLS_PER_EXTRACTION=2
ENABLE_FEW_SHOT_SINGLE_PASS=false
TOKEN_BUDGET_TARGET_AVG=15000
```

## Active Config Fields

### Required

- `ANTHROPIC_API_KEY`

### Database

- `DATABASE_URL`
- `DB_HOST`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_PORT`

### Runtime

- `MODEL_NAME`
- `LOG_LEVEL`
- `MAX_VERIFY_CALLS_PER_EXTRACTION`
- `ENABLE_FEW_SHOT_SINGLE_PASS`
- `TOKEN_BUDGET_TARGET_AVG`

## Usage

```python
from config import CONFIG

print(CONFIG.MODEL_NAME)
print(CONFIG.DB_PORT)
```

## Helper Methods

- `CONFIG.get_db_connection_string()`
- `CONFIG.validate_db_credentials(require_db=False)`
