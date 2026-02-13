# Database Tools Guide

Guide for using database lookup tools to check existing records and link to units during PLA officer data extraction.

## Overview

The SDK provides two database lookup tools designed to work with Claude API:

1. **`lookup_existing_officer`** - Search for existing officer records
2. **`lookup_unit_by_name`** - Look up PLA units to get unit IDs

These tools help prevent duplicate entries and link officer data to existing units.

---

## Connection Pooling

The database tools use **psycopg2 connection pooling** for efficiency:

- **Pool size:** 1-10 connections
- **Thread-safe:** Can be used in multi-threaded applications
- **UTF-8 encoding:** Proper handling of Chinese characters
- **Automatic cleanup:** Connections returned to pool after use

---

## 1. Officer Lookup Tool

### `LOOKUP_OFFICER_TOOL`

Search the database for an existing officer record by name.

**Purpose:**
- Check if officer already exists in database
- Avoid creating duplicate records
- Retrieve existing data for context
- Update existing records instead of creating new ones

**Tool Definition:**
```python
from tools import LOOKUP_OFFICER_TOOL

# Use with Claude API
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    tools=[LOOKUP_OFFICER_TOOL],
    messages=[...]
)
```

**Input Schema:**
```json
{
  "name": "林炳尧"
}
```

### Using the Tool

```python
from tools import execute_lookup_officer

tool_input = {"name": "林炳尧"}
result = execute_lookup_officer(tool_input)

if result.success and result.data.get('found'):
    # Officer exists
    officer = result.data['officer']
    print(f"Found existing officer: {officer['full_name']}")
    print(f"ID: {officer['id']}")
    print(f"Birth date: {officer['birth_date']}")
else:
    # Officer not in database
    print("Officer not found - can create new record")
```

### Success Response - Officer Found

```json
{
  "found": true,
  "officer": {
    "id": 123,
    "full_name": "林炳尧",
    "name_pinyin": "Lin Bingyao",
    "birth_date": "1943-01-01",
    "death_date": "2025-08-18",
    "birth_place": "福建晋江",
    "ethnicity": "汉族",
    "data": { /* JSONB field with full officer data */ },
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-02-09T14:20:00"
  },
  "message": "Found existing record for 林炳尧"
}
```

### Success Response - Officer Not Found

```json
{
  "found": false,
  "message": "No existing record found for 林炳尧"
}
```

### Error Response

```json
{
  "error": "Database error: connection refused"
}
```

---

## 2. Unit Lookup Tool

### `LOOKUP_UNIT_TOOL`

Look up a PLA unit by name to get the unit_id.

**Purpose:**
- Link promotions to specific units
- Get unit IDs for foreign key relationships
- Handle variations in unit naming
- Support fuzzy matching for flexibility

**Tool Definition:**
```python
from tools import LOOKUP_UNIT_TOOL

# Use with Claude API
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    tools=[LOOKUP_UNIT_TOOL],
    messages=[...]
)
```

**Input Schema:**
```json
{
  "unit_name": "南京军区"
}
```

### Using the Tool

```python
from tools import execute_lookup_unit

tool_input = {"unit_name": "南京军区"}
result = execute_lookup_unit(tool_input)

if result.success and result.data.get('found'):
    # Unit exists
    unit = result.data['unit']
    print(f"Unit ID: {unit['unit_id']}")
    print(f"Unit name: {unit['unit_name']}")
    print(f"Theater: {unit['theater_command']}")
else:
    # Unit not in database
    print("Unit not found")
```

### Success Response - Unit Found

```json
{
  "found": true,
  "unit": {
    "unit_id": 42,
    "unit_name": "南京军区",
    "unit_type": "军区",
    "parent_unit_id": null,
    "theater_command": "东部战区",
    "created_at": "2025-01-01T00:00:00"
  },
  "message": "Found unit: 南京军区 (ID: 42)"
}
```

### Fuzzy Matching

The tool supports fuzzy matching for unit name variations:

```python
# All these might match the same unit:
execute_lookup_unit({"unit_name": "南京军区"})
execute_lookup_unit({"unit_name": "南京"})  # Partial match
execute_lookup_unit({"unit_name": "Nanjing Military Region"})  # English

# Uses PostgreSQL ILIKE for case-insensitive partial matching
# Optionally uses pg_trgm for similarity scoring if available
```

---

## Database Schema

### Officers Table

```sql
CREATE TABLE pla_leaders (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL UNIQUE,
    name_pinyin VARCHAR(255),
    birth_date DATE,
    death_date DATE,
    birth_place VARCHAR(255),
    ethnicity VARCHAR(100),
    data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_pla_leaders_name ON pla_leaders(full_name);
CREATE INDEX idx_pla_leaders_birth_date ON pla_leaders(birth_date);
```

### Units Table

```sql
CREATE TABLE units (
    unit_id SERIAL PRIMARY KEY,
    unit_name VARCHAR(255) NOT NULL,
    unit_type VARCHAR(100),
    parent_unit_id INTEGER REFERENCES units(unit_id),
    theater_command VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index
CREATE INDEX idx_units_name ON units(unit_name);
```

### Initialize Database

```python
from tools.database_tools import initialize_database

# Creates tables and indexes if they don't exist
initialize_database()
```

---

## Complete Extraction Workflow

Using all tools together for robust officer extraction:

```python
from anthropic import Anthropic
from tools import (
    LOOKUP_OFFICER_TOOL,
    LOOKUP_UNIT_TOOL,
    VERIFY_INFORMATION_TOOL,
    VALIDATE_DATES_TOOL,
    SAVE_OFFICER_BIO_TOOL,
    execute_lookup_officer,
    execute_lookup_unit,
    execute_verify_information,
    execute_validate_dates,
    execute_save_officer_bio
)

client = Anthropic(api_key="your-key")

# Provide all tools to Claude
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    tools=[
        LOOKUP_OFFICER_TOOL,       # 1. Check if officer exists
        LOOKUP_UNIT_TOOL,           # 2. Look up unit IDs
        VERIFY_INFORMATION_TOOL,    # 3. Verify uncertain fields
        VALIDATE_DATES_TOOL,        # 4. Validate chronology
        SAVE_OFFICER_BIO_TOOL       # 5. Save final data
    ],
    messages=[{
        "role": "user",
        "content": f"""Extract officer bio from this obituary.

Process:
1. First, use lookup_existing_officer to check if this officer is already in our database
2. For any units mentioned, use lookup_unit_by_name to get unit IDs
3. Verify uncertain fields with verify_information_present
4. Validate dates with validate_dates
5. Save with save_officer_bio

Source text:
{source_text}"""
    }]
)

# Claude will use tools in sequence:
# - lookup_existing_officer("林炳尧") → found=false
# - lookup_unit_by_name("南京军区") → unit_id=42
# - verify_information_present(wife_name) → found=false
# - validate_dates(...) → success=true
# - save_officer_bio(...) → saves to database
```

---

## Handling Database Errors

### Connection Errors

```python
result = execute_lookup_officer({"name": "测试"})

if not result.success:
    if "connection" in result.error.lower():
        print("Database is not available")
        # Handle gracefully - maybe cache for later
    else:
        print(f"Database error: {result.error}")
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "connection refused" | PostgreSQL not running | Start PostgreSQL service |
| "authentication failed" | Wrong credentials | Check .env DATABASE_URL |
| "relation does not exist" | Tables not created | Run `initialize_database()` |
| "encoding error" | UTF-8 issue | Check `client_encoding='UTF8'` in config |

---

## Prompt Engineering

### Encourage Database Lookups

```python
prompt = """Extract officer biography.

IMPORTANT: Before creating a new record:
1. Use lookup_existing_officer to check if officer exists
2. If found, note the existing data and update if needed
3. For units in promotions, use lookup_unit_by_name to get unit IDs

Obituary:
{text}"""
```

### Handle Existing Officers

```python
# After Claude calls lookup_existing_officer
if result.data.get('found'):
    existing_officer = result.data['officer']

    update_prompt = f"""This officer already exists in our database:
    - ID: {existing_officer['id']}
    - Current data: {existing_officer['data']}

    Compare the obituary with existing data.
    Update any new or corrected information."""
```

---

## Best Practices

### 1. Always Check for Duplicates

```python
# Before extracting
prompt = "First, check if this officer exists using lookup_existing_officer"
```

### 2. Link to Units

```python
# For each promotion
prompt = "For each unit mentioned, use lookup_unit_by_name to get the unit_id"
```

### 3. Handle Missing Units

```python
result = execute_lookup_unit({"unit_name": "新单位"})

if not result.data.get('found'):
    # Unit doesn't exist - could create it or note for manual review
    print(f"New unit encountered: 新单位")
```

### 4. UTF-8 Encoding

All database operations use UTF-8 encoding:

```python
# Connection pool automatically sets client_encoding='UTF8'
# This ensures proper handling of Chinese characters
```

### 5. Connection Pooling Benefits

- **Performance:** Reuse connections instead of creating new ones
- **Concurrency:** Support multiple simultaneous queries
- **Resource management:** Automatic cleanup of idle connections

---

## Testing

Run the database tools test suite:

```bash
python test_database_tools.py
```

Tests cover:
- ✓ Tool definition structure
- ✓ Input validation
- ✓ Error handling
- ✓ Anthropic API compatibility
- ✓ Database schema creation

**Note:** Tests will show warnings if database is not configured. This is expected.

---

## Configuration

Ensure your `.env` file has database credentials:

```bash
# Database Configuration
DATABASE_URL=postgresql://pla_user:hoyasaxa@localhost:5432/pla_db

# Or use individual variables:
# DB_HOST=localhost
# DB_NAME=pla_db
# DB_USER=pla_user
# DB_PASSWORD=hoyasaxa
# DB_PORT=5432
```

---

## Example: Complete Officer Lookup Flow

```python
from tools import execute_lookup_officer, execute_save_officer_bio

# Step 1: Check if officer exists
lookup_result = execute_lookup_officer({"name": "林炳尧"})

if lookup_result.data.get('found'):
    # Officer exists
    existing_id = lookup_result.data['officer']['id']
    print(f"Updating existing officer ID {existing_id}")

    # Extract new data...
    officer_data = {
        "name": "林炳尧",
        "source_url": "https://example.com",
        # ... other fields
    }

    # Save (will update existing record due to UNIQUE constraint)
    save_result = execute_save_officer_bio(officer_data)

else:
    # Officer doesn't exist - create new
    print("Creating new officer record")

    officer_data = {
        "name": "林炳尧",
        "source_url": "https://example.com",
        # ... other fields
    }

    save_result = execute_save_officer_bio(officer_data)
```

---

## Summary

### Tool Usage Order

1. **lookup_existing_officer** - Check for duplicates first
2. **lookup_unit_by_name** - Get unit IDs for linkage
3. **verify_information_present** - Verify uncertain fields
4. **validate_dates** - Check chronology
5. **save_officer_bio** - Save verified data

### Key Features

- ✓ Connection pooling for performance
- ✓ UTF-8 encoding for Chinese characters
- ✓ Fuzzy matching for unit names
- ✓ Graceful error handling
- ✓ Prevent duplicate officer records
- ✓ Link promotions to units via IDs

### Benefits

- **Data integrity:** Prevent duplicates
- **Relational links:** Connect officers to units
- **Performance:** Efficient connection pooling
- **Reliability:** Proper error handling
- **Internationalization:** UTF-8 support for Chinese
