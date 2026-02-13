# Batch Test Script - Quick Reference

Simple test script to verify batch processing functionality.

## Quick Start

### 1. Basic Test (No Database)

```bash
python batch_test.py
```

This will:
- Process the local `data/test_obituary.txt` file 3 times
- Simulate batch processing without fetching from URLs
- Generate batch report
- Show summary statistics
- Flag low-confidence extractions

### 2. Test with Database Saving

```bash
python batch_test.py --save-db
```

Saves high-confidence results (≥0.7) to PostgreSQL database.

### 3. Test with Real URLs

```bash
python batch_test.py --use-real-urls
```

Attempts to fetch obituaries from URLs in `data/test_urls.txt`.

**Note**: URLs in `test_urls.txt` are placeholders by default.

---

## What It Tests

✅ **BatchProcessor Initialization**
- SDK setup
- Rate limiting configuration
- Directory creation

✅ **Extraction Process**
- Multiple obituary processing
- Progress tracking
- Error handling

✅ **Quality Control**
- Confidence scoring
- Automatic review flagging
- Validation

✅ **Reporting**
- Batch statistics
- Tool usage analysis
- Cost estimation

✅ **Output Management**
- File saving
- Review flagging
- Report generation

---

## Output

### Console Output

```
================================================================================
                        Batch Processor Test Script
                Testing batch processing with data/test_urls.txt
================================================================================

Using local test obituary: data/test_obituary.txt
✓ Loaded test obituary (1234 characters)

Processing 3 test extractions...

Processing: 100%|████████████████████| 3/3 [00:45<00:00, 15.2s/extraction]

✓ Completed 3 extractions

Generating batch report...

================================================================================
                            Batch Test Summary
================================================================================

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃ Metric                       ┃ Value              ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ Total Processed              │ 3                  │
│ Successful                   │ 3 (100.0%)         │
│ Failed                       │ 0                  │
│ Flagged for Review           │ 0                  │
└──────────────────────────────┴────────────────────┘

Individual Results:

┏━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ # ┃ Officer Name       ┃ Confidence ┃ Tokens   ┃ Tools ┃ Status        ┃
┡━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━┩
│ 1 │ 林炳尧             │ 0.85       │ 47,169   │ 9     │ ✓ Good        │
│ 2 │ 林炳尧             │ 0.85       │ 47,169   │ 9     │ ✓ Good        │
│ 3 │ 林炳尧             │ 0.85       │ 47,169   │ 9     │ ✓ Good        │
└───┴────────────────────┴────────────┴──────────┴───────┴───────────────┘

Cost Estimation:
  Total tokens: 141,507
  Estimated cost: $0.5704
  Average cost per extraction: $0.1901

================================================================================

✓ Batch test completed successfully!

╭─────────────────────── 📋 What's Next? ────────────────────────╮
│ Next Steps:                                                     │
│                                                                 │
│ 1. Check output/ directory for extraction results              │
│ 2. Review output/needs_review/ for flagged items               │
│ 3. Read output/batch_report_*.txt for detailed statistics      │
│ 4. Check batch_processing.log for detailed logs                │
╰─────────────────────────────────────────────────────────────────╯
```

### Generated Files

```
output/
├── 林炳尧_20260211_150000.json        # Extraction #1
├── 林炳尧_20260211_150015.json        # Extraction #2
├── 林炳尧_20260211_150030.json        # Extraction #3
├── batch_report_20260211_150045.txt  # Batch statistics
└── needs_review/                      # (empty if all pass)

batch_processing.log                   # Detailed logs
```

---

## Command-Line Options

```
usage: batch_test.py [-h] [--save-db] [--use-real-urls] [--rate-limit RATE_LIMIT]

optional arguments:
  -h, --help            show this help message and exit
  --save-db             Save high-confidence results to database
  --use-real-urls       Try to fetch from URLs (default: use local test file)
  --rate-limit RATE_LIMIT
                        Seconds between requests (default: 1.0)
```

---

## How It Works

### Default Mode (Local Test File)

1. **Loads** `data/test_obituary.txt`
2. **Processes** it 3 times with different URLs
3. **Applies** rate limiting between extractions
4. **Saves** results to `output/` directory
5. **Flags** low-confidence results (<0.7)
6. **Generates** comprehensive batch report

### Real URL Mode (`--use-real-urls`)

1. **Reads** URLs from `data/test_urls.txt`
2. **Fetches** obituary text from each URL
3. **Processes** each obituary
4. **Same** saving/flagging/reporting as default mode

**Note**: Real URL mode requires valid, accessible obituary URLs.

---

## Test Scenarios

### Scenario 1: Basic Functionality

```bash
python batch_test.py
```

**Expected**: 3 successful extractions, no failures, batch report generated.

### Scenario 2: Database Integration

```bash
python batch_test.py --save-db
```

**Expected**: Same as Scenario 1, plus database saves for high-confidence results.

**Requirements**: PostgreSQL configured in `.env`

### Scenario 3: Custom Rate Limit

```bash
python batch_test.py --rate-limit 2.0
```

**Expected**: 2 seconds between extractions, takes longer but safer for API limits.

### Scenario 4: Real URLs (When Available)

```bash
# First, add real URLs to data/test_urls.txt
nano data/test_urls.txt

# Then run
python batch_test.py --use-real-urls
```

**Expected**: Fetches from URLs, processes obituaries, generates report.

---

## Troubleshooting

### Issue: "data/test_obituary.txt not found"

**Solution**: Create test obituary file:
```bash
# Copy an existing obituary or create new one
echo "林炳尧同志逝世..." > data/test_obituary.txt
```

### Issue: Database errors with `--save-db`

**Solution**: Either:
1. Configure PostgreSQL in `.env`
2. Don't use `--save-db` flag (database is optional)

### Issue: All results flagged for review

**Possible causes**:
- Test obituary is incomplete/malformed
- Confidence threshold needs adjustment

**Solution**: Check `output/needs_review/*.json` for specific reasons.

### Issue: High costs

The test processes 3 extractions (~$0.60 total).

**Solution**: This is expected for testing. Adjust test count if needed.

---

## Customization

### Change Number of Test Iterations

Edit `batch_test.py`, line ~62:

```python
# Change from 3 to desired number
urls = [
    "https://www.news.cn/test/obituary_1.html",
    "https://www.news.cn/test/obituary_2.html",
    "https://www.news.cn/test/obituary_3.html",
    # Add more...
]
```

### Change Confidence Threshold

Edit `batch_test.py`, line ~92:

```python
# Change from 0.7 to desired threshold
if confidence < 0.7:  # Change this value
    processor.flag_for_review(...)
```

### Use Different Test File

```bash
# Create custom test file
echo "Your obituary text..." > data/custom_obituary.txt

# Edit batch_test.py line ~44 to use custom file
test_file = Path("data/custom_obituary.txt")
```

---

## What to Check After Running

### 1. Console Output
- Success rate (should be 100% for test)
- Confidence scores (should be >0.7)
- Token usage (should be ~38K-50K per extraction)

### 2. Output Files
```bash
# List extraction results
ls -lh output/*.json

# Count results
ls output/*.json | wc -l

# Check if any flagged
ls output/needs_review/
```

### 3. Batch Report
```bash
# Read report
cat output/batch_report_*.txt

# Check statistics
grep "Success Rate" output/batch_report_*.txt
grep "Average Confidence" output/batch_report_*.txt
```

### 4. Logs
```bash
# View logs
cat batch_processing.log

# Check for errors
grep ERROR batch_processing.log

# Check for warnings
grep WARNING batch_processing.log
```

---

## Integration with Real Workflow

Once testing is successful:

1. **Replace placeholder URLs** in `data/test_urls.txt` with real URLs
2. **Run with real URLs**: `python batch_test.py --use-real-urls`
3. **Enable database saving**: Add `--save-db` flag
4. **Scale up**: Use `batch_processor.py` for larger batches

---

## Performance Expectations

Based on default settings:

| Metric | Value |
|--------|-------|
| Extractions | 3 |
| Time | ~45-60 seconds |
| Tokens | ~140K total |
| Cost | ~$0.57 |
| Success Rate | ~100% (test data) |

**Note**: Real obituaries may have lower success rates depending on quality.

---

## Next Steps After Testing

1. ✅ **Verify all tests pass**
2. 📝 **Add real obituary URLs to `data/test_urls.txt`**
3. 🌐 **Test with real URLs**: `python batch_test.py --use-real-urls`
4. 💾 **Enable database saving**: Add `--save-db`
5. 📈 **Scale to production**: Use `batch_processor.py` for larger batches

---

Generated: 2026-02-11
