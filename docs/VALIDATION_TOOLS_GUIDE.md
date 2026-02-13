# Validation Tools Guide

Guide for using validation tools to ensure data quality and prevent hallucination during PLA officer data extraction.

## Overview

The SDK provides two validation tools designed to work with Claude API:

1. **`validate_dates`** - Checks chronological consistency of dates
2. **`verify_information_present`** - Verifies information exists in source text

These tools help Claude self-validate its extractions and avoid hallucination.

---

## 1. Date Validation Tool

### `VALIDATE_DATES_TOOL`

Checks if extracted dates are chronologically consistent.

**Purpose:**
- Verify enlistment date comes before promotions
- Ensure promotions are in chronological order
- Check birth/death date logic
- Detect impossible date combinations

**Tool Definition:**
```python
from tools import VALIDATE_DATES_TOOL

# Use with Claude API
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    tools=[VALIDATE_DATES_TOOL],
    messages=[...]
)
```

**Input Schema:**
```json
{
  "enlistment_date": "1961",
  "party_membership_date": "1964",
  "promotions": [
    {"rank": "少将", "date": "1995"},
    {"rank": "中将", "date": "2002"}
  ],
  "birth_date": "1943",
  "death_date": "2025-08-18"
}
```

### Validation Rules

1. **Birth Date Checks:**
   - Birth before enlistment
   - Birth before all promotions
   - Birth before death

2. **Enlistment Date Checks:**
   - Enlistment before all promotions
   - Enlistment before/after party membership (warning if after)

3. **Death Date Checks:**
   - Death after birth
   - Death after enlistment

4. **Promotion Chronology:**
   - Promotions in ascending order by date

### Using the Tool

```python
from tools import execute_validate_dates

# After Claude extracts dates
tool_input = {
    "enlistment_date": "1961",
    "party_membership_date": "1964",
    "promotions": [
        {"rank": "少将", "date": "1995"},
        {"rank": "中将", "date": "2002"}
    ],
    "birth_date": "1943",
    "death_date": "2025-08-18"
}

result = execute_validate_dates(tool_input)

if result.success:
    print("✓ All dates are consistent")
    print(f"Checked: {result.data['checked']}")
else:
    print(f"✗ Date inconsistencies found:")
    print(result.error)
```

### Example Success Case

**Input:**
```python
{
    "birth_date": "1943",
    "enlistment_date": "1961",
    "party_membership_date": "1964",
    "promotions": [
        {"rank": "少将", "date": "1995"},
        {"rank": "中将", "date": "2002"}
    ]
}
```

**Output:**
```json
{
  "message": "Dates validated successfully",
  "warnings": [],
  "checked": {
    "birth_year": 1943,
    "enlistment_year": 1961,
    "party_year": 1964,
    "promotion_count": 2
  }
}
```

### Example Error Case

**Input:**
```python
{
    "enlistment_date": "1990",
    "promotions": [
        {"rank": "少将", "date": "1985"}  # Before enlistment!
    ]
}
```

**Error Message:**
```
Date inconsistencies found:
 - Enlistment date 1990 is after promotion to 少将 in 1985
```

---

## 2. Information Verification Tool

### `VERIFY_INFORMATION_TOOL`

Double-checks if specific information is actually mentioned in the source text.

**Purpose:**
- Prevent hallucination
- Verify uncertain extractions
- Confirm presence of optional fields
- Provide evidence for extracted data

**Tool Definition:**
```python
from tools import VERIFY_INFORMATION_TOOL

# Use with Claude API
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    tools=[VERIFY_INFORMATION_TOOL],
    messages=[...]
)
```

**Input Schema:**
```json
{
  "field_name": "wife_name",
  "search_terms": ["夫人", "妻子", "配偶"],
  "obituary_text": "林炳尧同志的夫人是张三..."
}
```

### Common Use Cases

#### 1. Verify Wife's Name
```python
{
  "field_name": "wife_name",
  "search_terms": ["夫人", "妻子", "配偶", "爱人"],
  "obituary_text": obituary_text
}
```

#### 2. Verify Retirement Date
```python
{
  "field_name": "retirement_date",
  "search_terms": ["退休", "离休", "退役"],
  "obituary_text": obituary_text
}
```

#### 3. Verify Ethnicity
```python
{
  "field_name": "ethnicity",
  "search_terms": ["汉族", "满族", "回族", "蒙古族", "藏族"],
  "obituary_text": obituary_text
}
```

#### 4. Verify Specific Award
```python
{
  "field_name": "specific_award",
  "search_terms": ["一级红星功勋荣誉章", "八一勋章"],
  "obituary_text": obituary_text
}
```

### Using the Tool

```python
from tools import execute_verify_information

tool_input = {
    "field_name": "wife_name",
    "search_terms": ["夫人", "妻子", "配偶"],
    "obituary_text": obituary_text
}

result = execute_verify_information(tool_input)

if result.data['found']:
    print(f"✓ Found {result.data['field_name']}")
    print(f"Matched: {result.data['matched_terms']}")
    print(f"Excerpts: {result.data['excerpts']}")
else:
    print(f"✗ {result.data['field_name']} not mentioned in text")
    print(f"Searched: {result.data['searched_terms']}")
```

### Example - Information Found

**Input:**
```python
{
  "field_name": "wife_name",
  "search_terms": ["夫人", "妻子"],
  "obituary_text": "林炳尧同志的夫人是张三，两人育有一子一女。"
}
```

**Output:**
```json
{
  "field_name": "wife_name",
  "found": true,
  "matched_terms": ["夫人"],
  "excerpt_count": 1,
  "excerpts": [
    "林炳尧同志的夫人是张三，两人育有一子一女。"
  ],
  "message": "Found 1 mention(s) of wife_name in the text."
}
```

### Example - Information Not Found

**Input:**
```python
{
  "field_name": "wife_name",
  "search_terms": ["夫人", "妻子"],
  "obituary_text": "林炳尧同志于8月18日逝世，享年82岁。"
}
```

**Output:**
```json
{
  "field_name": "wife_name",
  "found": false,
  "searched_terms": ["夫人", "妻子"],
  "message": "No mention of wife_name found in the text. Searched for: 夫人, 妻子"
}
```

**Important:** When `found=false`, Claude should set that field to `null` in the final extraction.

---

## Complete Extraction Workflow

Here's how to use all three tools together for robust extraction:

```python
from anthropic import Anthropic
from tools import (
    SAVE_OFFICER_BIO_TOOL,
    VALIDATE_DATES_TOOL,
    VERIFY_INFORMATION_TOOL,
    execute_save_officer_bio,
    execute_validate_dates,
    execute_verify_information
)

client = Anthropic(api_key="your-key")

# Step 1: Initial extraction with all tools available
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    tools=[
        VERIFY_INFORMATION_TOOL,  # Use first to check uncertain fields
        VALIDATE_DATES_TOOL,       # Use second to validate dates
        SAVE_OFFICER_BIO_TOOL      # Use last to save final data
    ],
    messages=[{
        "role": "user",
        "content": f"""Extract biographical information from this source.

Follow this process:
1. First, if you're uncertain about any optional fields (wife_name, ethnicity, etc.),
   use verify_information_present to check if they're mentioned.
2. Before finalizing, use validate_dates to check date consistency.
3. Finally, use save_officer_bio to save the complete data.

Source text:
{source_text}"""
    }]
)

# Step 2: Process tool calls
messages = [{"role": "user", "content": source_text}]

for block in response.content:
    if block.type == "tool_use":
        if block.name == "verify_information_present":
            result = execute_verify_information(block.input)
            # Return result to Claude
            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result.to_dict())
                }]
            })

        elif block.name == "validate_dates":
            result = execute_validate_dates(block.input)
            # Check if validation passed
            if not result.success:
                # Alert Claude to fix the dates
                messages.append({"role": "assistant", "content": response.content})
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result.to_dict())
                    }]
                })

        elif block.name == "save_officer_bio":
            result = execute_save_officer_bio(block.input)
            if result.success:
                officer_data = result.data['officer_bio']
                # Save to file or database
                print(f"✓ Extracted: {officer_data['name']}")
```

---

## Prompt Engineering Best Practices

### Encourage Tool Use

```python
prompt = """Extract officer biography from this obituary.

IMPORTANT: Follow these steps:
1. If uncertain about optional fields (wife_name, ethnicity), use verify_information_present
2. Before saving, use validate_dates to check chronological consistency
3. Use save_officer_bio only after verification

Obituary:
{text}"""
```

### Handle Verification Results

```python
prompt = """Extract officer biography.

For optional fields like wife_name or ethnicity:
- If mentioned, extract the value
- If uncertain, use verify_information_present to check
- If verification returns found=false, set field to null

Obituary:
{text}"""
```

### Handle Validation Errors

```python
# After date validation fails
retry_prompt = """The dates you extracted have inconsistencies:
{validation_errors}

Please review the obituary again and fix the dates, then revalidate."""
```

---

## Common Search Terms

### For Wife/Spouse
```python
["夫人", "妻子", "配偶", "爱人"]
```

### For Ethnicity
```python
["汉族", "满族", "回族", "蒙古族", "藏族", "维吾尔族", "壮族"]
```

### For Retirement
```python
["退休", "离休", "退役", "离职"]
```

### For Education
```python
["毕业", "学习", "大学", "学院", "学位", "深造"]
```

### For Awards
```python
["勋章", "功勋", "荣誉", "奖章", "八一勋章", "一级红星"]
```

---

## Testing

Run the validation tools test suite:

```bash
python test_validation_tools.py
```

Tests cover:
- ✓ Date validation with valid dates
- ✓ Error detection (promotion before enlistment)
- ✓ Error detection (death before birth)
- ✓ Information verification (found)
- ✓ Information verification (not found)
- ✓ Ethnicity verification
- ✓ Anthropic API compatibility

---

## Error Handling

### Date Validation Errors

Common errors and their meanings:

| Error | Meaning | Action |
|-------|---------|--------|
| "Enlistment date X is after promotion date Y" | Impossible chronology | Re-extract dates from text |
| "Death date X is before birth date Y" | Logical impossibility | Check for typos in dates |
| "Promotion to X in year Y is after promotion to Z in year W" | Promotions out of order | Verify promotion sequence |

### Verification Tool Usage

**When to use:**
- ✓ When a field is optional and you're uncertain
- ✓ For control variables (wife_name, ethnicity)
- ✓ For ambiguous mentions in text

**When NOT to use:**
- ✗ For required fields already clearly stated
- ✗ For information you're confident about
- ✗ Excessively (limit to 2-3 verifications per extraction)

---

## Integration Example

Complete example showing all tools in action:

```python
from anthropic import Anthropic
from tools import *

client = Anthropic(api_key="your-key")

obituary = """林炳尧是福建晋江人，1961年入伍，1964年加入中国共产党。
他1995年晋升为少将军衔，2002年晋升为中将军衔。"""

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    tools=[
        VERIFY_INFORMATION_TOOL,
        VALIDATE_DATES_TOOL,
        SAVE_OFFICER_BIO_TOOL
    ],
    messages=[{
        "role": "user",
        "content": f"""Extract officer info. Steps:
1. Check uncertain fields with verify_information_present
2. Validate dates with validate_dates
3. Save with save_officer_bio

Obituary: {obituary}"""
    }]
)

# Claude will:
# 1. Call verify_information_present for wife_name (not found → set to null)
# 2. Call validate_dates with extracted dates (validates chronology)
# 3. Call save_officer_bio with final data
```

---

## Summary

### Tool Usage Order

1. **verify_information_present** - First, to check uncertain fields
2. **validate_dates** - Second, to validate chronology
3. **save_officer_bio** - Last, to save verified data

### Key Benefits

- ✓ Prevents hallucination through source text verification
- ✓ Catches date inconsistencies automatically
- ✓ Provides evidence for extracted data
- ✓ Improves data quality and confidence
- ✓ Self-validating extraction workflow

### Best Practices

1. Use verification sparingly (only for uncertain fields)
2. Always validate dates before saving
3. Handle tool results in conversation flow
4. Set fields to null when verification fails
5. Iterate on errors until validation passes
