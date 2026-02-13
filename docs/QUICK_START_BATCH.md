# Quick Start: Batch Processing

Get started with batch processing in 3 minutes.

## 📦 What Was Added

### New Files
```
pla-agent-sdk/
├── batch_processor.py           ← Main batch processor
├── batch_test.py               ← Test script
├── data/
│   └── test_urls.txt           ← Sample URL list
├── BATCH_PROCESSING_GUIDE.md   ← Full documentation
└── BATCH_TEST_README.md        ← Test guide
```

### Updated Files
```
├── README.md                    ← Added batch processing section
├── requirements.txt             ← Added tqdm dependency
└── CHANGES.md                   ← Documented new feature
```

---

## 🚀 3-Minute Quick Start

### Step 1: Install Dependencies (30 seconds)

```bash
cd "/Users/jack/Documents/Documents/College Stuff/Clubs/2025-26/Concord Group/PLA Data Project/pla-agent-sdk"

pip install tqdm
```

### Step 2: Run Test (2 minutes)

```bash
python batch_test.py
```

**What happens:**
- Processes local test obituary 3 times
- Shows progress bar
- Generates batch report
- Displays summary statistics

**Expected output:**
```
Processing 3 test extractions...
Processing: 100%|████████████| 3/3 [00:45<00:00, 15.2s/extraction]
✓ Completed 3 extractions

Total Processed:  3
Successful:       3 (100.0%)
Average Tokens:   47,169
Estimated Cost:   $0.57
```

### Step 3: Check Results (30 seconds)

```bash
# View extraction results
ls output/*.json

# Read batch report
cat output/batch_report_*.txt

# Check for flagged items
ls output/needs_review/
```

---

## 🎯 Common Use Cases

### Use Case 1: Test Batch Processing

```bash
python batch_test.py
```

**When**: First time using batch processor
**Purpose**: Verify everything works
**Cost**: ~$0.57 (3 extractions)

---

### Use Case 2: Test with Database

```bash
python batch_test.py --save-db
```

**When**: Testing database integration
**Purpose**: Verify DB saves work
**Requires**: PostgreSQL configured in `.env`

---

### Use Case 3: Process Real URLs

```bash
# 1. Add real URLs to file
nano data/test_urls.txt

# 2. Process them
python batch_test.py --use-real-urls
```

**When**: Have real obituary URLs
**Purpose**: Process actual data
**Note**: Fetches from web

---

### Use Case 4: Large Batch (Production)

```bash
# 1. Create URL list
cat > urls.txt << EOF
https://www.news.cn/obituary1.html
https://www.news.cn/obituary2.html
https://www.news.cn/obituary3.html
...
EOF

# 2. Process with batch_processor
python batch_processor.py urls.txt --save-to-db
```

**When**: Processing many obituaries
**Purpose**: Production use
**Recommended**: Start with small batches

---

## 📊 What You Get

### 1. Individual Extraction Files

```json
{
  "officer_bio": {
    "name": "林炳尧",
    "confidence_score": 0.85,
    "birth_date": "1943",
    ...
  },
  "tool_calls": [...],
  "total_tokens": 47169,
  "success": true
}
```

**Location**: `output/{name}_{timestamp}.json`

---

### 2. Batch Report

```
================================================================================
SUMMARY STATISTICS
================================================================================
Total Processed:           3
Successful Extractions:    3
Success Rate:              100.0%
Average Confidence Score:  0.847

================================================================================
PERFORMANCE METRICS
================================================================================
Total Tokens:              141,507
Average Tokens/Extract:    47,169
```

**Location**: `output/batch_report_{timestamp}.txt`

---

### 3. Flagged Items (if any)

Low-confidence or failed extractions automatically saved to:

**Location**: `output/needs_review/REVIEW_{name}_{timestamp}.json`

**Contents**:
```json
{
  "officer_bio": {...},
  "review_reason": "Low confidence score: 0.62",
  "flagged_at": "2026-02-11T14:30:45"
}
```

---

## 🔧 Configuration

### Change Rate Limit

```bash
# Default: 1 second between requests
python batch_test.py --rate-limit 2.0
```

**When to adjust**:
- Large batches: Increase to 2-3 seconds
- Small batches: Can use 1 second
- API errors: Increase rate limit

---

### Change Confidence Threshold

Edit `batch_processor.py` line ~250:

```python
if confidence < 0.7:  # Change this value
    self.flag_for_review(...)
```

**Recommendations**:
- Strict: 0.8 (fewer false positives)
- Balanced: 0.7 (default)
- Lenient: 0.6 (more auto-approvals)

---

## 📝 File Formats

### URL List Format

**data/test_urls.txt**:
```
# Comments start with #
# One URL per line
# Blank lines ignored

https://www.news.cn/obituary1.html
https://www.news.cn/obituary2.html

# Another section
https://www.news.cn/obituary3.html
```

---

## 🐛 Troubleshooting

### Problem: "ModuleNotFoundError: No module named 'tqdm'"

**Solution**:
```bash
pip install tqdm
```

---

### Problem: "data/test_obituary.txt not found"

**Solution**:
```bash
# Check if file exists
ls data/test_obituary.txt

# If not, you need to add a test obituary
# Or use --use-real-urls flag
```

---

### Problem: All extractions fail

**Check**:
1. Is ANTHROPIC_API_KEY set in `.env`?
2. Is test obituary file valid Chinese text?
3. Check logs: `cat batch_processing.log`

---

### Problem: Database errors with --save-db

**Solutions**:
1. Don't use `--save-db` (database is optional)
2. Or configure PostgreSQL in `.env`:
   ```
   DATABASE_URL=postgresql://user:pass@localhost:5432/pla_db
   ```

---

## 💰 Cost Estimates

Based on Sonnet 4.5 pricing ($3/M input, $15/M output):

| Batch Size | Avg Tokens | Est. Cost |
|------------|------------|-----------|
| 10 URLs    | 470K       | $1.90     |
| 25 URLs    | 1.2M       | $4.75     |
| 50 URLs    | 2.4M       | $9.50     |
| 100 URLs   | 4.7M       | $19.00    |

**Per extraction**: ~$0.19

**Note**: Actual costs vary based on obituary length and complexity.

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| **BATCH_TEST_README.md** | How to use test script |
| **BATCH_PROCESSING_GUIDE.md** | Complete batch processing docs |
| **README.md** | Overall SDK documentation |
| **CHANGES.md** | Recent changes and updates |

---

## ✅ Verification Checklist

Before production use:

- [ ] `pip install tqdm` completed
- [ ] `python batch_test.py` runs successfully
- [ ] Batch report generated in `output/`
- [ ] Success rate is ~100% for test data
- [ ] Individual JSON files created
- [ ] Logs show no errors: `cat batch_processing.log`
- [ ] Understand cost per extraction (~$0.19)
- [ ] `.env` has ANTHROPIC_API_KEY

---

## 🎓 Learning Path

### Beginner
1. Run `python batch_test.py`
2. Read console output
3. Check `output/` directory
4. Read batch report

### Intermediate
1. Add real URLs to `data/test_urls.txt`
2. Run with `--use-real-urls`
3. Review flagged items
4. Adjust confidence threshold

### Advanced
1. Use `batch_processor.py` for large batches
2. Enable database saving
3. Customize rate limiting
4. Integrate into automated pipeline

---

## 🚀 Next Steps

1. **Test**: Run `python batch_test.py` ✓
2. **Verify**: Check output files ✓
3. **Real Data**: Add real URLs to `test_urls.txt`
4. **Scale**: Use `batch_processor.py` for production
5. **Automate**: Integrate into your workflow

---

## 💡 Pro Tips

1. **Start Small**: Test with 5-10 URLs before large batches
2. **Monitor Costs**: Check batch reports for token usage
3. **Review Flagged Items**: Always check `needs_review/` directory
4. **Use Rate Limiting**: Prevents API throttling
5. **Read Logs**: `batch_processing.log` has detailed info
6. **Backup Results**: Archive `output/` periodically

---

## 📞 Getting Help

1. Check logs: `cat batch_processing.log`
2. Read documentation:
   - BATCH_TEST_README.md
   - BATCH_PROCESSING_GUIDE.md
3. Review examples in documentation
4. Check existing test files for reference

---

Generated: 2026-02-11
