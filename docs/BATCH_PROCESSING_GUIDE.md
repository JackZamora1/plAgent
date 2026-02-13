# Batch Processing Guide

Complete guide for using the BatchProcessor to extract PLA officer biographies from multiple obituaries.

## Quick Start

### 1. Basic Batch Processing

Process URLs from a file:
```bash
python batch_processor.py urls.txt
```

### 2. With Database Saving

Save high-confidence results (>0.7) to database:
```bash
python batch_processor.py urls.txt --save-to-db
```

### 3. Process Specific URLs

Process individual URLs directly:
```bash
python batch_processor.py --urls \
  "https://www.news.cn/2025/obituary1.html" \
  "https://www.news.cn/2025/obituary2.html"
```

### 4. Custom Rate Limiting

Adjust API rate limit (default: 1 second):
```bash
python batch_processor.py urls.txt --rate-limit 2.0
```

---

## Features

### ✓ Automatic Rate Limiting
- Default: 1 second between requests
- Prevents API throttling
- Configurable via `--rate-limit`

### ✓ Progress Tracking
- Real-time progress bar using tqdm
- Shows current URL being processed
- Tracks success/failure counts

### ✓ Automatic Review Flagging
- Flags results with confidence < 0.7
- Saves to `output/needs_review/`
- Includes reason for flagging

### ✓ Comprehensive Reporting
- Success rate statistics
- Average confidence scores
- Token usage analysis
- Tool usage breakdown
- Common failure patterns

### ✓ Error Handling
- Graceful error recovery
- Continues processing on failures
- Detailed logging to `batch_processing.log`

### ✓ Optional Database Integration
- Saves high-confidence results to PostgreSQL
- Uses existing `save_officer_bio_to_database()`
- Only saves if confidence ≥ 0.7

---

## Input File Format

Create a text file with one URL per line:

**urls.txt:**
```
https://www.news.cn/2025/obituary1.html
https://www.news.cn/2025/obituary2.html
https://www.news.cn/2025/obituary3.html

# You can add comments starting with #
# Blank lines are ignored

https://www.news.cn/2025/obituary4.html
```

---

## Output Structure

```
output/
├── 林炳尧_20260211_143022.json        # Successful extraction
├── 张三_20260211_143045.json          # Another extraction
├── batch_report_20260211_143100.txt  # Batch report
└── needs_review/
    ├── REVIEW_李四_20260211_143030.json   # Low confidence
    └── REVIEW_unknown_20260211_143055.json # Failed extraction
```

---

## Output Files

### 1. Individual Extraction Results

Each successful extraction creates a JSON file:
- **Filename**: `{officer_name}_{timestamp}.json`
- **Contents**: Full AgentExtractionResult with tool calls, tokens, etc.

Example:
```json
{
  "officer_bio": {
    "name": "林炳尧",
    "pinyin_name": "Lín Bǐngyáo",
    "hometown": "福建省晋江市",
    "birth_date": "1943",
    "confidence_score": 0.85,
    ...
  },
  "tool_calls": [...],
  "total_input_tokens": 34641,
  "total_output_tokens": 2967,
  "success": true,
  "source_url": "https://..."
}
```

### 2. Review-Flagged Results

Low-confidence or failed extractions go to `output/needs_review/`:
- **Filename**: `REVIEW_{officer_name}_{timestamp}.json`
- **Additional fields**: `review_reason`, `flagged_at`

Example:
```json
{
  "officer_bio": {...},
  "review_reason": "Low confidence score: 0.62",
  "flagged_at": "2026-02-11T14:30:45",
  ...
}
```

### 3. Batch Report

Comprehensive statistics saved to `batch_report_{timestamp}.txt`:

```
================================================================================
PLA AGENT SDK - BATCH PROCESSING REPORT
================================================================================
Generated: 2026-02-11 14:31:00

================================================================================
SUMMARY STATISTICS
================================================================================
Total Processed:           25
Successful Extractions:    23
Failed Extractions:        2
Success Rate:              92.0%
Flagged for Review:        3

================================================================================
QUALITY METRICS
================================================================================
Average Confidence Score:  0.847
Min Confidence:            0.620
Max Confidence:            0.980

================================================================================
PERFORMANCE METRICS
================================================================================
Total Input Tokens:        867,025
Total Output Tokens:       74,175
Total Tokens:              941,200
Average Tokens/Extract:    37,648
Average Tool Calls:        6.2
Average Conversation Turns: 6.8

================================================================================
TOOL USAGE
================================================================================
save_officer_bio                 48 calls  (95.8% success)
verify_information_present       92 calls  (100.0% success)
validate_dates                   23 calls  (100.0% success)
lookup_existing_officer          23 calls  (0.0% success)  # DB not configured
lookup_unit_by_name             46 calls  (0.0% success)  # DB not configured
```

---

## Usage Examples

### Example 1: Simple Batch Processing

```bash
# Create URL file
cat > my_urls.txt << EOF
https://www.news.cn/2025/obituary1.html
https://www.news.cn/2025/obituary2.html
https://www.news.cn/2025/obituary3.html
EOF

# Process
python batch_processor.py my_urls.txt
```

### Example 2: With Database

```bash
# Make sure database is configured in .env
# DATABASE_URL=postgresql://user:pass@localhost:5432/pla_db

python batch_processor.py urls.txt --save-to-db
```

### Example 3: Programmatic Usage

```python
from batch_processor import BatchProcessor

# Initialize
processor = BatchProcessor(require_db=False, rate_limit_seconds=1.5)

# Process URLs
urls = [
    "https://www.news.cn/2025/obituary1.html",
    "https://www.news.cn/2025/obituary2.html",
]
results = processor.process_urls(urls, save_to_db=False)

# Generate report
processor.generate_batch_report(results)

# Check results
for result in results:
    if result.success:
        officer = result.officer_bio
        print(f"✓ {officer.name} - Confidence: {officer.confidence_score:.2f}")
    else:
        print(f"✗ Failed: {result.error_message}")
```

### Example 4: Process from File

```python
from batch_processor import BatchProcessor

processor = BatchProcessor()
results = processor.process_from_file('urls.txt', save_to_db=True)
processor.generate_batch_report(results)
```

---

## Rate Limiting

### Why Rate Limiting?

- Prevents API throttling
- Avoids hitting Anthropic rate limits
- Ensures stable processing

### Configuration

```bash
# 1 second between requests (default)
python batch_processor.py urls.txt

# 2 seconds between requests (more conservative)
python batch_processor.py urls.txt --rate-limit 2.0

# 0.5 seconds between requests (faster, but riskier)
python batch_processor.py urls.txt --rate-limit 0.5
```

### Recommendations

- **Small batches (<10 URLs)**: 1 second is fine
- **Medium batches (10-50 URLs)**: 1-2 seconds recommended
- **Large batches (>50 URLs)**: 2-3 seconds to be safe

---

## Review Workflow

### Automatic Flagging

Results are flagged for review when:
1. **Low confidence** (< 0.7)
2. **Extraction failed** (parsing errors, validation errors)
3. **Missing critical fields** (name, source_url)

### Manual Review Process

1. **Check flagged files**:
   ```bash
   ls output/needs_review/
   ```

2. **Review JSON files**:
   ```bash
   cat output/needs_review/REVIEW_*.json | jq
   ```

3. **Fix issues**:
   - Low confidence: Verify extracted data manually
   - Failed extraction: Check source URL, retry if needed
   - Missing fields: Manually add missing information

4. **Re-process if needed**:
   ```python
   from batch_processor import BatchProcessor

   processor = BatchProcessor()
   results = processor.process_urls(['problem_url.html'])
   ```

---

## Logging

### Log Files

All processing is logged to `batch_processing.log`:
```
2026-02-11 14:30:15 - batch_processor - INFO - Initializing BatchProcessor...
2026-02-11 14:30:16 - batch_processor - INFO - ✓ PLAgentSDK initialized successfully
2026-02-11 14:30:18 - batch_processor - INFO - Fetching obituary from: https://...
2026-02-11 14:30:20 - batch_processor - INFO - ✓ Extracted 1234 characters
2026-02-11 14:30:22 - batch_processor - INFO - Extracting biography for URL 1/25
...
```

### Log Levels

- **INFO**: Normal processing events
- **WARNING**: Flagged for review, retries, recoverable errors
- **ERROR**: Failed extractions, network errors, exceptions

### Viewing Logs

```bash
# View full log
cat batch_processing.log

# View only errors
grep ERROR batch_processing.log

# View warnings and errors
grep -E "WARNING|ERROR" batch_processing.log

# Follow log in real-time
tail -f batch_processing.log
```

---

## Performance Optimization

### Threading (Future Enhancement)

The `BatchProcessor` includes a `threading.Lock` for future parallelization:

```python
# Future implementation example
from concurrent.futures import ThreadPoolExecutor

def process_urls_parallel(self, urls, save_to_db=False, max_workers=3):
    """Process URLs in parallel with thread safety."""
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(self._process_single_url, url)
                   for url in urls]
        for future in futures:
            results.append(future.result())
    return results
```

**Note**: Parallelism is not yet implemented to avoid rate limit issues.

### Token Usage Optimization

- Average: ~38K tokens per extraction
- Cost: ~$0.19 per extraction (Sonnet 4.5)
- For 100 obituaries: ~$19

**Tips**:
- Use smaller batches to test first
- Monitor `batch_report` for token usage
- Consider using cheaper model for low-priority extractions

---

## Troubleshooting

### Issue: "ANTHROPIC_API_KEY is required"

**Solution**: Add API key to `.env`:
```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
```

### Issue: "Database error: relation does not exist"

**Solution**: Database tools are optional. Either:
1. Don't use `--save-to-db` flag
2. Initialize database schema first

### Issue: Rate limit errors (429)

**Solution**: Increase rate limit:
```bash
python batch_processor.py urls.txt --rate-limit 3.0
```

### Issue: All extractions flagged for review

**Possible causes**:
- URLs are invalid or not Xinhua format
- Obituaries are too short or malformed
- System prompt needs adjustment

**Solution**: Check a few URLs manually first

### Issue: Network timeouts

**Solution**:
- Check internet connection
- Verify URLs are accessible
- Increase timeout in `_fetch_obituary()` method

---

## Best Practices

### 1. Test First
```bash
# Test with 2-3 URLs first
python batch_processor.py --urls \
  "https://www.news.cn/test1.html" \
  "https://www.news.cn/test2.html"
```

### 2. Review Flagged Results
Always check `output/needs_review/` after batch processing.

### 3. Monitor Logs
Keep an eye on `batch_processing.log` during processing.

### 4. Backup Results
```bash
# Backup output directory
tar -czf output_backup_$(date +%Y%m%d).tar.gz output/
```

### 5. Incremental Processing
Process in batches of 20-50 URLs to avoid long-running sessions.

---

## Advanced Usage

### Custom Confidence Threshold

Edit `batch_processor.py` to change the review threshold:

```python
# Change from 0.7 to 0.8
if confidence < 0.8:  # Line ~250
    self.flag_for_review(...)
```

### Custom Database Logic

Override `save_to_db` behavior:

```python
from batch_processor import BatchProcessor

class CustomProcessor(BatchProcessor):
    def _should_save_to_db(self, result):
        """Custom logic for database saving."""
        if not result.success:
            return False

        officer = result.officer_bio
        # Only save if name and birth_date are present
        return (officer.confidence_score >= 0.8 and
                officer.birth_date is not None)
```

### Export to CSV

```python
import csv
from batch_processor import BatchProcessor

processor = BatchProcessor()
results = processor.process_from_file('urls.txt')

# Export to CSV
with open('output/results.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Name', 'Confidence', 'Birth Date', 'Hometown', 'URL'])

    for r in results:
        if r.success and r.officer_bio:
            o = r.officer_bio
            writer.writerow([o.name, o.confidence_score,
                           o.birth_date, o.hometown, o.source_url])
```

---

## CLI Reference

```
usage: batch_processor.py [-h] [--urls URLS [URLS ...]] [--save-to-db]
                         [--require-db] [--rate-limit RATE_LIMIT]
                         [input_file]

Batch process PLA officer obituaries

positional arguments:
  input_file            File containing URLs (one per line)

optional arguments:
  -h, --help            show this help message and exit
  --urls URLS [URLS ...]
                        Process specific URLs directly
  --save-to-db          Save high-confidence results to database
  --require-db          Require database connection
  --rate-limit RATE_LIMIT
                        Seconds to wait between requests (default: 1.0)
```

---

## Next Steps

1. **Test with sample URLs**: Create `urls.txt` with 2-3 test URLs
2. **Run batch processing**: `python batch_processor.py urls.txt`
3. **Review results**: Check `output/` and `output/needs_review/`
4. **Generate report**: Reports are auto-generated after processing
5. **Scale up**: Process larger batches once comfortable

---

Generated: 2026-02-11
