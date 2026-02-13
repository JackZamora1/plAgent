# Schema Guide - PLA Agent SDK

Comprehensive guide to using the Pydantic models for PLA leadership data extraction.

## Models Overview

### 1. Promotion
Tracks military rank promotions with dates and units.

```python
from schema import Promotion

promotion = Promotion(
    rank="少将",           # Required: Military rank
    date="1995",           # Optional: YYYY or YYYY-MM-DD
    unit="南京军区"        # Optional: Unit name
)
```

**Validation:**
- `rank` cannot be empty
- `date` must be YYYY or YYYY-MM-DD format

---

### 2. OfficerBio
Comprehensive biographical information for PLA officers.

```python
from schema import OfficerBio

officer = OfficerBio(
    # Required fields
    name="林炳尧",
    source_url="https://www.news.cn/example/c.html",

    # Identity
    pinyin_name="Lin Bingyao",
    hometown="福建晋江",
    birth_date="1943",

    # Military service
    enlistment_date="1961",
    party_membership_date="1964",
    retirement_date="2010",
    death_date="2025-08-18",

    # Political participation
    congress_participation=["第十五次全国代表大会"],
    cppcc_participation=["第十一届全国委员会委员"],

    # Career
    promotions=[
        Promotion(rank="少将", date="1995"),
        Promotion(rank="中将", date="2002")
    ],
    notable_positions=["原南京军区副司令员", "军长"],
    awards=["一级红星功勋荣誉章"],

    # Control variables
    wife_name="张三",

    # Extraction metadata
    confidence_score=0.95,
    extraction_notes="High confidence from official obituary"
)
```

**Validation:**
- `name` and `source_url` are required
- All dates must be YYYY or YYYY-MM-DD format
- Death date cannot be before birth date
- Enlistment date cannot be before birth date
- Retirement date cannot be before enlistment date
- `confidence_score` must be between 0.0 and 1.0

**Methods:**
```python
# Convert to dictionary
officer_dict = officer.to_dict(exclude_none=True)

# Convert to JSON string
json_str = officer.to_json(exclude_none=True, indent=2)

# Get extraction schema for Claude API
schema = OfficerBio.get_extraction_schema()
```

---

### 3. ToolResult
Tracks individual tool execution results.

```python
from schema import ToolResult

# Successful tool call
result = ToolResult(
    tool_name="extract_text_from_url",
    success=True,
    data={"text_length": 1234, "encoding": "utf-8"}
)

# Failed tool call
result = ToolResult(
    tool_name="database_save",
    success=False,
    error="Connection timeout"
)
```

**Validation:**
- If `success=False`, `error` message must be provided

---

### 4. AgentExtractionResult
Tracks overall agent extraction process and performance.

```python
from schema import AgentExtractionResult, OfficerBio, ToolResult

result = AgentExtractionResult(
    # Extraction result
    officer_bio=officer,

    # Tool tracking
    tool_calls=[
        ToolResult(tool_name="extract_text", success=True),
        ToolResult(tool_name="validate_data", success=True)
    ],

    # Performance metrics
    conversation_turns=3,
    total_input_tokens=1500,
    total_output_tokens=800,

    # Status
    success=True,
    error_message=None
)

# Get summary statistics
summary = result.get_summary()
print(f"Total tokens: {result.get_total_tokens()}")
print(f"Tool success rate: {result.get_success_rate():.1%}")
```

**Validation:**
- If `success=True`, `officer_bio` must be provided
- If `success=False`, `error_message` must be provided

**Methods:**
```python
# Get total tokens
total = result.get_total_tokens()

# Get tool success rate
rate = result.get_success_rate()

# Get summary
summary = result.get_summary()

# Convert to dict/JSON
result.to_dict(exclude_none=True)
result.to_json(exclude_none=True)
```

---

## Usage Examples

### Creating Officer Bio from Obituary

```python
from schema import OfficerBio, Promotion

officer = OfficerBio(
    name="林炳尧",
    pinyin_name="Lin Bingyao",
    hometown="福建晋江",
    birth_date="1943",
    enlistment_date="1961",
    party_membership_date="1964",
    death_date="2025-08-18",
    congress_participation=["第十五次全国代表大会"],
    cppcc_participation=["第十一届全国委员会委员"],
    promotions=[
        Promotion(rank="少将", date="1995"),
        Promotion(rank="中将", date="2002")
    ],
    notable_positions=["原南京军区副司令员"],
    source_url="https://www.news.cn/20250901/example/c.html",
    confidence_score=0.95
)

# Save to JSON file
import json
with open('output/officer_bio.json', 'w', encoding='utf-8') as f:
    f.write(officer.to_json(exclude_none=True))
```

### Tracking Agent Extraction

```python
from schema import AgentExtractionResult, OfficerBio, ToolResult

# Track tool calls
tool_calls = []

# Tool 1: Extract text
tool_calls.append(ToolResult(
    tool_name="extract_text_from_url",
    success=True,
    data={"text_length": 1234}
))

# Tool 2: Validate
tool_calls.append(ToolResult(
    tool_name="validate_officer_data",
    success=True,
    data={"is_valid": True}
))

# Create result
extraction_result = AgentExtractionResult(
    officer_bio=officer,
    tool_calls=tool_calls,
    conversation_turns=3,
    total_input_tokens=1500,
    total_output_tokens=800,
    success=True
)

# Print summary
print(extraction_result.get_summary())
```

### Using with Claude API (Tool Schema)

```python
from schema import OfficerBio

# Get schema for Claude API tool definition
extraction_schema = OfficerBio.get_extraction_schema()

# Use in Claude API tool definition
tool_definition = {
    "name": "extract_officer_bio",
    "description": "Extract PLA officer biographical information",
    "input_schema": extraction_schema
}
```

---

## Field Reference

### OfficerBio Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | str | ✓ | Chinese name |
| `source_url` | str | ✓ | Source URL |
| `pinyin_name` | str | | Romanized name |
| `hometown` | str | | Birthplace |
| `birth_date` | str | | Birth date (YYYY or YYYY-MM-DD) |
| `enlistment_date` | str | | Military join date |
| `party_membership_date` | str | | CCP join date |
| `retirement_date` | str | | Retirement date (control var) |
| `death_date` | str | | Death date |
| `congress_participation` | List[str] | | CCP Congress participations |
| `cppcc_participation` | List[str] | | CPPCC participations |
| `promotions` | List[Promotion] | | Rank promotions |
| `notable_positions` | List[str] | | Key positions held |
| `awards` | List[str] | | Military awards |
| `wife_name` | str | | Spouse name (control var) |
| `confidence_score` | float | | Extraction confidence (0.0-1.0) |
| `extraction_notes` | str | | Agent's reasoning |
| `extracted_at` | datetime | | Extraction timestamp (auto) |

---

## Error Handling

All models use Pydantic validation. Handle errors appropriately:

```python
from pydantic import ValidationError
from schema import OfficerBio

try:
    officer = OfficerBio(
        name="",  # Empty name - will fail
        source_url="https://example.com"
    )
except ValidationError as e:
    print(f"Validation error: {e}")
    # Handle specific errors
    for error in e.errors():
        field = error['loc']
        message = error['msg']
        print(f"{field}: {message}")
```

---

## Testing

Run the schema test suite:

```bash
python test_schema.py
```

This validates:
- ✓ Promotion model with date validation
- ✓ OfficerBio model with comprehensive fields
- ✓ Date logic validation (death before birth, etc.)
- ✓ ToolResult model with error handling
- ✓ AgentExtractionResult with metrics
- ✓ JSON serialization/deserialization
- ✓ Schema generation for Claude API

---

## Legacy Compatibility

The old `PLALeader` model is still available for backwards compatibility:

```python
from schema import PLALeader, PersonalInfo, MilitaryPosition

leader = PLALeader(
    personal_info=PersonalInfo(
        full_name="林炳尧",
        name_pinyin="Lin Bingyao"
    ),
    military_positions=[
        MilitaryPosition(position_title="副司令员")
    ]
)
```

**Note:** New code should use `OfficerBio` instead.
