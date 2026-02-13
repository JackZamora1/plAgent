# Recommended Workflow Guide

Guide to the recommended tool sequence for high-quality extractions.

## 🎯 Overview

The agent follows a **7-step workflow** to ensure consistent, high-quality extractions:

1. **lookup_existing_officer** - Check for duplicates
2. **Extract information** - Read and extract from obituary
3. **verify_information_present** - Verify uncertain fields
4. **lookup_unit_by_name** - Enrich unit references (optional)
5. **validate_dates** - Ensure chronological consistency
6. **save_officer_bio** - Save extracted data (once)
7. **save_to_database** - Persist to PostgreSQL (optional)

---

## 📋 Step-by-Step Workflow

### **Step 1: Check for Existing Officer**

```
Tool: lookup_existing_officer
Purpose: Check if officer already in database
Status: First tool call
```

**Why first?**
- Prevents duplicate entries
- Allows for updates instead of new records
- Provides context for extraction

**Expected:**
- Usually fails (database not initialized) - that's OK
- If found, note existing data for comparison

---

### **Step 2: Extract Biographical Information**

```
Tool: None (internal processing)
Purpose: Read obituary and extract facts
```

**What to extract:**
- ✅ Name (Chinese)
- ✅ Pinyin name (transliterate if not in text)
- ✅ Hometown, birth date, death date
- ✅ Enlistment, party membership dates
- ✅ ALL positions (not just senior roles)
- ✅ Promotions (only explicit ones)
- ✅ Awards, political participation

**Key principle:** Only extract what's explicitly stated

---

### **Step 3: Verify Uncertain Fields**

```
Tool: verify_information_present (multiple calls)
Purpose: Confirm absence of optional fields
Required for: wife_name, retirement_date, congress_participation, cppcc_participation
```

**Example calls:**
```python
verify_information_present(
    field_name="wife_name",
    search_terms=["妻子", "夫人", "配偶", "爱人"]
)

verify_information_present(
    field_name="retirement_date",
    search_terms=["退休", "离休", "离职", "退役"]
)

verify_information_present(
    field_name="congress_participation",
    search_terms=["全国代表大会", "党代会", "代表"]
)

verify_information_present(
    field_name="cppcc_participation",
    search_terms=["全国委员会", "政协", "委员"]
)
```

**Why important:**
- Prevents hallucination
- Catches buried information
- Ensures thoroughness
- Mandatory for quality

**Expected:** 2-4 calls minimum

---

### **Step 4: Look Up Units (Optional)**

```
Tool: lookup_unit_by_name
Purpose: Link positions to known military units
When: Any unit reference in positions
```

**Example calls:**
```python
lookup_unit_by_name(unit_name="某集团军")
lookup_unit_by_name(unit_name="南京军区")
lookup_unit_by_name(unit_name="某师")
```

**Why useful:**
- Enriches data with unit IDs
- Enables organizational analysis
- Links to known structures

**Expected:** 0-3 calls depending on obituary

---

### **Step 5: Validate Chronological Consistency**

```
Tool: validate_dates
Purpose: Ensure dates are chronologically consistent
When: Before saving
```

**What it checks:**
- Birth < Enlistment
- Enlistment < Party membership
- Birth < Death
- Promotions in chronological order

**Expected:** 1 call before save

---

### **Step 6: Save Extracted Data**

```
Tool: save_officer_bio
Purpose: Validate schema and save extraction
When: After all verification and validation
Important: Call ONLY ONCE
```

**What to include:**
- All extracted fields
- confidence_score (0.0-1.0)
- extraction_notes (reasoning, uncertainties)
- source_url

**Why only once:**
- Multiple saves waste tokens
- Indicates extraction issues
- Confuses result tracking

**Expected:** Exactly 1 successful call

---

### **Step 7: Persist to Database (Optional)**

```
Tool: save_to_database
Purpose: Store in PostgreSQL for long-term use
When: High confidence (≥ 0.8) and no errors
```

**Criteria for calling:**
- confidence_score >= 0.8
- No validation errors
- save_officer_bio succeeded

**Expected:** 0-1 calls

---

## ✅ Ideal Tool Sequence

### **Example 1: Complete Workflow**

```
1. lookup_existing_officer      → Failed (DB not init) ✓
2. verify_information_present   → wife_name not found ✓
3. verify_information_present   → retirement_date not found ✓
4. verify_information_present   → congress_participation not found ✓
5. verify_information_present   → cppcc_participation not found ✓
6. lookup_unit_by_name          → 某集团军 ✓
7. lookup_unit_by_name          → 南京军区 ✓
8. validate_dates               → Dates valid ✓
9. save_officer_bio             → Saved ✓
```

**Score:** ✓ Perfect - All steps followed correctly

---

### **Example 2: Minimal Workflow**

```
1. lookup_existing_officer      → Failed (DB not init) ✓
2. verify_information_present   → wife_name not found ✓
3. verify_information_present   → retirement_date not found ✓
4. validate_dates               → Dates valid ✓
5. save_officer_bio             → Saved ✓
```

**Score:** ✓ Good - Core steps followed

---

### **Example 3: Problematic Workflow**

```
1. save_officer_bio             → Failed (validation) ✗
2. verify_information_present   → wife_name ✗
3. save_officer_bio             → Saved ✗
```

**Issues:**
- ✗ No lookup_existing_officer
- ✗ save_officer_bio called first (should be last)
- ✗ Only 1 verify call (should be 2-4)
- ✗ No validate_dates
- ✗ save_officer_bio called twice

**Score:** ✗ Poor - Major sequence violations

---

## 🧪 Testing Workflow Adherence

### **Run Workflow Test**

```bash
python test_workflow.py
```

**Expected output:**
```
Testing Agent Workflow Adherence

✓ Loaded 1,234 characters
✓ SDK initialized

Running extraction...

✓ Extraction Successful: 林炳尧
  Confidence: 0.85
  Tokens: 47,169

Tool Call Sequence:
┌────┬─────────────────────────────┬──────────┬────────────────────┐
│ #  │ Tool Name                   │ Status   │ Notes              │
├────┼─────────────────────────────┼──────────┼────────────────────┤
│ 1  │ lookup_existing_officer     │ ✗        │ Check for...       │
│ 2  │ verify_information_present  │ ✓        │ Verify: wife_name  │
│ 3  │ verify_information_present  │ ✓        │ Verify: retire...  │
│ 4  │ validate_dates              │ ✓        │ Date validation    │
│ 5  │ save_officer_bio            │ ✓        │ Save extraction    │
└────┴─────────────────────────────┴──────────┴────────────────────┘

Workflow Analysis:
┌──────────────────────────────────────┬─────────────────┐
│ Check                                │ Status          │
├──────────────────────────────────────┼─────────────────┤
│ Step 1: lookup_existing_officer      │ ✓ PASS          │
│ Step 3: verify_information_present   │ ✓ PASS          │
│ Step 4: validate_dates               │ ✓ PASS          │
│ Step 5: save_officer_bio (once)      │ ✓ PASS          │
└──────────────────────────────────────┴─────────────────┘

✓ No sequence issues - workflow followed correctly!

✓ WORKFLOW TEST PASSED
```

---

## 📊 Quality Metrics

### **Good Workflow Indicators**

✅ **lookup_existing_officer is first**
✅ **2-4 verify_information_present calls**
✅ **validate_dates before save_officer_bio**
✅ **save_officer_bio called exactly once**
✅ **save_to_database only if confident**

### **Warning Signs**

⚠️ **0-1 verify calls** - Missing verification
⚠️ **Multiple save_officer_bio calls** - Retry loops
⚠️ **validate after save** - Wrong order
⚠️ **No lookup_existing_officer** - Missing duplicate check

### **Critical Issues**

❌ **save_officer_bio multiple times** - Wasting tokens
❌ **No validation** - Quality risk
❌ **No verification** - Hallucination risk

---

## 🎯 Confidence Scoring Guidelines

Based on workflow completeness:

**0.9-1.0: Excellent**
- All workflow steps followed
- 4+ verify calls
- All optional fields checked
- Dates validated
- No uncertainties

**0.7-0.8: Good**
- Core workflow followed
- 2-3 verify calls
- Dates validated
- Minor uncertainties

**0.5-0.6: Acceptable**
- Some workflow steps skipped
- 1-2 verify calls
- Some missing data

**Below 0.5: Poor**
- Workflow not followed
- No verification
- Major gaps

---

## 💡 Pro Tips

### 1. Verification is Mandatory

Always verify uncertain fields:
```
✓ verify wife_name before setting null
✓ verify retirement_date before setting null
✓ verify congress_participation before setting null
✓ verify cppcc_participation before setting null
```

### 2. Validate Before Save

```
✓ Call validate_dates BEFORE save_officer_bio
✗ Don't save without validation
```

### 3. Save Only Once

```
✓ Extract → Verify → Validate → Save (once)
✗ Don't retry save_officer_bio multiple times
```

### 4. Use Lookup

```
✓ Call lookup_existing_officer first
✗ Don't skip duplicate checking
```

### 5. Enrich with Units

```
✓ Call lookup_unit_by_name for units
✗ Don't ignore unit references
```

---

## 🐛 Troubleshooting

### Issue: Multiple save_officer_bio calls

**Cause:** Validation failures trigger retries
**Fix:** Ensure data is correct before first save

### Issue: No verify calls

**Cause:** Agent skipping verification
**Fix:** System prompt emphasizes mandatory verification

### Issue: Wrong sequence

**Cause:** Agent not following workflow
**Fix:** User message reinforces workflow

### Issue: Low verification count

**Cause:** Only checking some fields
**Fix:** Check ALL uncertain fields (wife, retire, congress, cppcc)

---

## 📚 See Also

- **agent.py** - System prompt with workflow
- **test_workflow.py** - Workflow testing script
- **CHANGES.md** - Recent workflow updates

---

Generated: 2026-02-11
