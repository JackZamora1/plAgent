# Configuration Guide

Complete guide to the PLA Agent SDK configuration system using Pydantic BaseSettings.

---

## Overview

The configuration system uses **Pydantic BaseSettings** for:
- ✅ Automatic `.env` file loading
- ✅ Type validation and coercion
- ✅ Clear error messages for missing values
- ✅ Environment variable parsing
- ✅ IDE autocomplete support

---

## Quick Start

### 1. Create `.env` File

```bash
# Required
ANTHROPIC_API_KEY=your_api_key_here

# Database (Option A: Connection URL)
DATABASE_URL=postgresql://user:password@localhost:5432/pla_db

# Database (Option B: Individual variables)
DB_HOST=localhost
DB_NAME=pla_leadership
DB_USER=pla_user
DB_PASSWORD=your_password
DB_PORT=5432

# Optional (defaults provided)
MAX_ITERATIONS=10
MODEL_NAME=claude-sonnet-4-20250514
LOG_LEVEL=INFO
```

### 2. Import CONFIG

```python
from config import CONFIG

# Access configuration values
print(CONFIG.ANTHROPIC_API_KEY)  # Auto-loaded from .env
print(CONFIG.MODEL_NAME)          # "claude-sonnet-4-20250514"
print(CONFIG.MAX_ITERATIONS)      # 10 (int type)
```

---

## Configuration Reference

### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `ANTHROPIC_API_KEY` | `str` | Anthropic API key | `sk-ant-...` |

### Database Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `DATABASE_URL` | `Optional[str]` | `None` | PostgreSQL connection URL |
| `DB_HOST` | `str` | `"localhost"` | Database host |
| `DB_NAME` | `str` | `"pla_leadership"` | Database name |
| `DB_USER` | `Optional[str]` | `None` | Database user |
| `DB_PASSWORD` | `Optional[str]` | `None` | Database password |
| `DB_PORT` | `int` | `5432` | Database port |

**Note:** If `DATABASE_URL` is provided, it will be parsed to populate the individual `DB_*` fields automatically.

### Agent Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `MAX_ITERATIONS` | `int` | `10` | Maximum agentic loop iterations |
| `MODEL_NAME` | `str` | `"claude-sonnet-4-20250514"` | Claude model ID |
| `LOG_LEVEL` | `str` | `"INFO"` | Logging level (DEBUG, INFO, WARNING, ERROR) |

---

## Using the Configuration

### Global CONFIG Instance

The recommended way to use configuration is through the global `CONFIG` instance:

```python
from config import CONFIG

# Access values
api_key = CONFIG.ANTHROPIC_API_KEY
max_iter = CONFIG.MAX_ITERATIONS  # Type: int

# Use in your code
from anthropic import Anthropic

client = Anthropic(api_key=CONFIG.ANTHROPIC_API_KEY)
```

### Type Safety

Pydantic automatically validates and converts types:

```python
# In .env:
# MAX_ITERATIONS=20
# DB_PORT=5433

# In code:
print(type(CONFIG.MAX_ITERATIONS))  # <class 'int'>
print(type(CONFIG.DB_PORT))         # <class 'int'>
print(type(CONFIG.MODEL_NAME))      # <class 'str'>

# No manual conversion needed!
for i in range(CONFIG.MAX_ITERATIONS):  # Works directly
    ...
```

---

## Configuration Methods

### 1. `get_db_connection_string()`

Get PostgreSQL connection string.

```python
from config import CONFIG

conn_str = CONFIG.get_db_connection_string()
# Returns: "postgresql://user:pass@localhost:5432/pla_db"
```

**Returns:**
- If `DATABASE_URL` is set: returns `DATABASE_URL`
- Otherwise: constructs from individual `DB_*` fields

### 2. `validate_db_credentials(require_db: bool = False)`

Validate database credentials are present.

```python
from config import CONFIG

# Optional validation (no error if missing)
CONFIG.validate_db_credentials(require_db=False)

# Required validation (raises ValueError if missing)
try:
    CONFIG.validate_db_credentials(require_db=True)
except ValueError as e:
    print(f"Database not configured: {e}")
```

**Parameters:**
- `require_db` (`bool`): If `True`, raises `ValueError` if credentials missing

**Raises:**
- `ValueError`: If `require_db=True` and `DB_USER` or `DB_PASSWORD` is missing

---

## Advanced Features

### DATABASE_URL Parsing

When you provide `DATABASE_URL`, it's automatically parsed to populate individual fields:

```python
# In .env:
# DATABASE_URL=postgresql://myuser:mypass@db.example.com:5433/mydb

# Automatically sets:
# DB_HOST = "db.example.com"
# DB_NAME = "mydb"
# DB_USER = "myuser"
# DB_PASSWORD = "mypass"
# DB_PORT = 5433

# Access either way:
print(CONFIG.DATABASE_URL)  # Original URL
print(CONFIG.DB_HOST)       # "db.example.com"
```

**Priority:** Explicit environment variables override `DATABASE_URL` parsing:

```bash
# If both are set:
DATABASE_URL=postgresql://user1:pass1@host1:5432/db1
DB_HOST=custom_host

# Result:
# DB_HOST = "custom_host"  (explicit value takes precedence)
# DB_USER = "user1"        (from DATABASE_URL)
```

### Pydantic Model Methods

Since `CONFIG` is a Pydantic model, you get all Pydantic features:

```python
from config import CONFIG

# Export as dict
config_dict = CONFIG.model_dump()
print(config_dict)
# {'ANTHROPIC_API_KEY': '...', 'DB_HOST': 'localhost', ...}

# Export as JSON
config_json = CONFIG.model_dump_json(indent=2)

# Exclude sensitive fields
safe_dict = CONFIG.model_dump(exclude={'ANTHROPIC_API_KEY', 'DB_PASSWORD'})
```

---

## Function: `load_config()`

Alternative way to load configuration as a dictionary:

```python
from config import load_config

config = load_config()
# Returns: {'ANTHROPIC_API_KEY': '...', 'DB_HOST': '...', ...}

print(config['ANTHROPIC_API_KEY'])
print(config['MAX_ITERATIONS'])  # Note: String "10", not int
```

**Use Cases:**
- When you need a simple dict
- For debugging/logging all config values
- For passing to legacy code

**Note:** `load_config()` returns string values. Use `CONFIG` instance for typed access.

---

## Error Handling

### Missing API Key

```python
# If ANTHROPIC_API_KEY not in .env:

from config import CONFIG
# Raises: ValidationError: Field required [type=missing]

# Or with load_config():
from config import load_config
config = load_config()
# Raises: ValueError: ANTHROPIC_API_KEY is required but not found
```

**Error Message:**
```
ANTHROPIC_API_KEY is required but not found in environment.

Please add it to your .env file:
  ANTHROPIC_API_KEY=your_key_here

Get your API key from: https://console.anthropic.com/
```

### Missing Database Credentials

```python
# If database required but credentials missing:

CONFIG.validate_db_credentials(require_db=True)
# Raises: ValueError with helpful message
```

**Error Message:**
```
Database credentials are required but not found.

Please add to your .env file either:
  DATABASE_URL=postgresql://user:pass@host:port/dbname

Or individual variables:
  DB_USER=your_user
  DB_PASSWORD=your_password
  DB_HOST=localhost
  DB_NAME=pla_leadership
  DB_PORT=5432
```

---

## Migration from Old Config

### Old Code (Class-based)

```python
from config import Config

# Access via class attributes
api_key = Config.ANTHROPIC_API_KEY
db_host = Config.DB_HOST

# Validate
Config.validate(require_db=True)
```

### New Code (Instance-based)

```python
from config import CONFIG

# Access via instance
api_key = CONFIG.ANTHROPIC_API_KEY
db_host = CONFIG.DB_HOST

# Validate
CONFIG.validate_db_credentials(require_db=True)
```

### Backward Compatibility

The old `Config.validate()` class method is preserved for compatibility:

```python
from config import Config

# Still works (calls CONFIG.validate_db_credentials internally)
Config.validate(require_db=True)
```

**Recommendation:** Use `CONFIG.validate_db_credentials()` in new code.

---

## Usage Examples

### Example 1: Basic Usage

```python
from config import CONFIG
from anthropic import Anthropic

# Initialize client
client = Anthropic(api_key=CONFIG.ANTHROPIC_API_KEY)

# Use model name from config
response = client.messages.create(
    model=CONFIG.MODEL_NAME,
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}]
)
```

### Example 2: Database Connection

```python
from config import CONFIG
import psycopg2

# Validate credentials first
CONFIG.validate_db_credentials(require_db=True)

# Connect using connection string
conn = psycopg2.connect(CONFIG.get_db_connection_string())

# Or use individual fields
conn = psycopg2.connect(
    host=CONFIG.DB_HOST,
    database=CONFIG.DB_NAME,
    user=CONFIG.DB_USER,
    password=CONFIG.DB_PASSWORD,
    port=CONFIG.DB_PORT
)
```

### Example 3: Conditional Database Usage

```python
from config import CONFIG

# Check if DB is configured (without raising error)
try:
    CONFIG.validate_db_credentials(require_db=True)
    use_database = True
except ValueError:
    use_database = False

if use_database:
    # Use database tools
    from tools.database_tools import lookup_existing_officer
    ...
else:
    # Skip database features
    print("Database not configured - skipping lookups")
```

### Example 4: Logging Configuration

```python
from config import CONFIG
import logging

# Use LOG_LEVEL from config
logging.basicConfig(
    level=getattr(logging, CONFIG.LOG_LEVEL),  # "INFO" -> logging.INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.info(f"Using model: {CONFIG.MODEL_NAME}")
logger.info(f"Max iterations: {CONFIG.MAX_ITERATIONS}")
```

---

## Testing Configuration

Run the test suite:

```bash
python test_config.py
```

**Tests:**
- ✓ `load_config()` function
- ✓ `CONFIG` instance attributes
- ✓ Type validation (int, str conversions)
- ✓ `get_db_connection_string()` method
- ✓ `validate_db_credentials()` method
- ✓ Pydantic features (`model_dump()`, `model_dump_json()`)
- ✓ Backward compatibility with `Config.validate()`

---

## Environment Variables Priority

Pydantic loads configuration in this order (highest to lowest priority):

1. **Explicitly set environment variables** (from shell)
2. **`.env` file values**
3. **Default values** (defined in `Config` class)

Example:

```python
# In Config class:
MODEL_NAME: str = Field("claude-sonnet-4-20250514", ...)

# Priority:
export MODEL_NAME="claude-opus-4-6"  # 1. Shell env (highest)
# .env: MODEL_NAME=claude-haiku-4-5  # 2. .env file
# Default: claude-sonnet-4-20250514   # 3. Default (lowest)

# Result: CONFIG.MODEL_NAME = "claude-opus-4-6"
```

---

## Best Practices

### 1. Use the Global CONFIG Instance

```python
# ✓ Good
from config import CONFIG
api_key = CONFIG.ANTHROPIC_API_KEY

# ✗ Avoid
from config import Config
config = Config()  # Creates new instance
```

### 2. Validate Early

```python
# At application startup
from config import CONFIG

CONFIG.validate_db_credentials(require_db=True)
# Now you know DB is configured before running queries
```

### 3. Don't Hardcode Defaults

```python
# ✗ Bad
max_iterations = 10

# ✓ Good
max_iterations = CONFIG.MAX_ITERATIONS
```

### 4. Use Type Hints

```python
from config import CONFIG

def process_data(iterations: int = CONFIG.MAX_ITERATIONS):
    # IDE knows iterations is int, provides autocomplete
    for i in range(iterations):
        ...
```

### 5. Never Commit `.env`

Add to `.gitignore`:

```gitignore
.env
.env.local
.env.*.local
```

Provide `.env.template` instead:

```bash
# .env.template
ANTHROPIC_API_KEY=
DATABASE_URL=
MAX_ITERATIONS=10
```

---

## Summary

### Key Components

| Component | Purpose |
|-----------|---------|
| `Config` class | Pydantic BaseSettings model |
| `CONFIG` instance | Global configuration object |
| `load_config()` | Load config as dict |
| `.env` file | Store configuration values |

### Key Features

- ✅ Automatic type validation
- ✅ Clear error messages
- ✅ IDE autocomplete
- ✅ DATABASE_URL parsing
- ✅ Backward compatibility
- ✅ Environment variable priority

### Migration Checklist

- [ ] Add `pydantic-settings` to requirements
- [ ] Replace `from config import Config` → `from config import CONFIG`
- [ ] Replace `Config.FIELD` → `CONFIG.FIELD`
- [ ] Replace `Config.validate()` → `CONFIG.validate_db_credentials()`
- [ ] Update type hints to use CONFIG values

The new configuration system makes it easier to manage settings with type safety and validation!
