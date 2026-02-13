# CLI Guide - PLA Agent SDK

Complete command-line interface for extracting PLA officer biographies.

## Quick Start

```bash
# Show help
python cli.py --help

# Show help for specific command
python cli.py extract --help
```

---

## Commands Overview

| Command | Description |
|---------|-------------|
| **extract** | Extract from single URL |
| **batch** | Process multiple URLs from file |
| **test** | Run test suite |
| **validate** | Re-validate saved extraction |
| **replay** | Replay saved conversation |
| **stats** | Show aggregate statistics |
| **interactive** | Interactive REPL mode (NEW!) |

---

## 1. extract - Single URL Extraction

Extract biography from a single obituary URL.

### Basic Usage

```bash
python cli.py extract --url "https://www.news.cn/obituary.html"
```

### With Database Saving

```bash
python cli.py extract --url "https://www.news.cn/obituary.html" --save-db
```

### Verbose Output

```bash
python cli.py extract --url "https://www.news.cn/obituary.html" --verbose
```

### Output

```
╭─────────────────────────────────────────╮
│     Extract PLA Officer Biography       │
│    URL: https://www.news.cn/...         │
╰─────────────────────────────────────────╯

✓ SDK initialized
✓ Fetched 1,234 characters
✓ Successfully extracted: 林炳尧

Extracted Information:
┌─────────────────────────┬──────────────────────┐
│ Name                    │ 林炳尧               │
│ Pinyin                  │ Lín Bǐngyáo          │
│ Hometown                │ 福建省晋江市         │
│ Birth Date              │ 1943                 │
│ Death Date              │ 2023-01-15           │
│ Confidence              │ 0.85                 │
└─────────────────────────┴──────────────────────┘

Performance Metrics:
┌─────────────────────────┬──────────────────────┐
│ Conversation Turns      │ 6                    │
│ Tool Calls              │ 9                    │
│ Total Tokens            │ 47,169               │
└─────────────────────────┴──────────────────────┘

✓ Saved to: output/林炳尧_20260211_160000.json
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--url` | Yes | Obituary URL |
| `--save-db` | No | Save to database if confidence ≥ 0.7 |
| `--verbose` | No | Show detailed conversation |

---

## 2. batch - Batch Processing

Process multiple URLs from a text file.

### Basic Usage

```bash
python cli.py batch --file urls.txt
```

### With Database Saving

```bash
python cli.py batch --file urls.txt --save-db
```

### Custom Rate Limit

```bash
python cli.py batch --file urls.txt --rate-limit 2.0
```

### With Parallel Processing (Future)

```bash
python cli.py batch --file urls.txt --parallel 3
```

**Note**: Parallel processing not yet implemented.

### Output

```
╭─────────────────────────────────────────╮
│         Batch Processing                │
│         File: urls.txt                  │
╰─────────────────────────────────────────╯

✓ Processor initialized

Processing obituaries: 100%|████████| 25/25 [06:15<00:00, 15.0s/obituary]

✓ Processed 25 URLs
  Successful: 23
  Failed: 2
  Flagged for review: 3
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--file`, `-f` | Yes | File with URLs (one per line) |
| `--save-db` | No | Save high-confidence results to DB |
| `--parallel`, `-p` | No | Number of workers (not implemented) |
| `--rate-limit` | No | Seconds between requests (default: 1.0) |

---

## 3. test - Test Suite

Run extraction tests on an obituary file.

### Basic Usage

```bash
python cli.py test
```

Uses default test file: `data/test_obituary.txt`

### Custom Test File

```bash
python cli.py test --obituary my_test.txt
```

### Output

```
╭─────────────────────────────────────────╮
│            Test Suite                   │
│      Running extraction tests           │
╰─────────────────────────────────────────╯

✓ Loaded 1,234 characters
✓ SDK initialized

Test Results:

┌─────────────────────────┬────────────┬──────────────────────┐
│ Test                    │ Status     │ Details              │
├─────────────────────────┼────────────┼──────────────────────┤
│ Extraction Success      │ ✓ PASS     │                      │
│ Required Fields         │ ✓ PASS     │ name, source_url     │
│ Confidence Score        │ ✓ PASS     │ 0.85 ≥ 0.7          │
│ Biographical Data       │ ✓ PASS     │                      │
│ Tool Usage              │ ✓ PASS     │ 9 tools used         │
│ Token Efficiency        │ ✓ PASS     │ 47,169 tokens        │
└─────────────────────────┴────────────┴──────────────────────┘

Results: 6/6 tests passed
✓ All tests passed!
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--obituary` | No | Test obituary file (default: data/test_obituary.txt) |

---

## 4. validate - Re-run Validation

Re-run validation on a saved extraction file.

### Basic Usage

```bash
python cli.py validate --json output/林炳尧_20260211.json
```

### Output

```
╭─────────────────────────────────────────╮
│        Validate Extraction              │
│   File: output/林炳尧_20260211.json     │
╰─────────────────────────────────────────╯

✓ Loaded extraction for: 林炳尧

Validation Results:

┌─────────────────────────┬────────────┬──────────────────────┐
│ Check                   │ Status     │ Details              │
├─────────────────────────┼────────────┼──────────────────────┤
│ Required Fields         │ ✓ PASS     │ name, source_url...  │
│ Date Format             │ ✓ PASS     │ All valid            │
│ Confidence Score        │ ✓ PASS     │ 0.85 in range [0,1]  │
│ Promotions              │ ✓ PASS     │ 2 promotions         │
└─────────────────────────┴────────────┴──────────────────────┘

Results: 4/4 checks passed
✓ All validation checks passed!
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--json` | Yes | Path to saved extraction JSON |

### Use Cases

- **Quality Control**: Verify old extractions meet new standards
- **Testing**: Test new validation rules on existing data
- **Debugging**: Identify validation issues

---

## 5. replay - Replay Conversation

Replay and display a saved extraction conversation.

### Basic Usage

```bash
python cli.py replay --json output/林炳尧_20260211.json
```

### Output

```
╭─────────────────────────────────────────╮
│       Replay Conversation               │
│   File: output/林炳尧_20260211.json     │
╰─────────────────────────────────────────╯

✓ Loaded extraction: 林炳尧

Extraction Summary:
  Status: Success
  Conversation Turns: 6
  Tool Calls: 9
  Total Tokens: 47,169

Tool Call Sequence:

┌────┬──────────────────────────────┬──────────┬────────────┐
│ #  │ Tool                         │ Status   │ Timestamp  │
├────┼──────────────────────────────┼──────────┼────────────┤
│ 1  │ lookup_existing_officer      │ ✗        │ 14:30:15   │
│ 2  │ verify_information_present   │ ✓        │ 14:30:21   │
│ 3  │ verify_information_present   │ ✓        │ 14:30:26   │
│ 4  │ validate_dates               │ ✓        │ 14:30:29   │
│ 5  │ save_officer_bio             │ ✗        │ 14:30:40   │
│ 6  │ save_officer_bio             │ ✓        │ 14:30:45   │
└────┴──────────────────────────────┴──────────┴────────────┘

Extracted Officer Bio:

{
  "name": "林炳尧",
  "pinyin_name": "Lín Bǐngyáo",
  "hometown": "福建省晋江市",
  ...
}
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--json` | Yes | Path to saved extraction JSON |

### Use Cases

- **Debugging**: Understand why extraction succeeded/failed
- **Learning**: See how Claude uses tools
- **Analysis**: Review tool call patterns

---

## 6. stats - Aggregate Statistics

Analyze all extractions in a directory.

### Basic Usage

```bash
python cli.py stats
```

Analyzes `output/` directory by default.

### Custom Directory

```bash
python cli.py stats --dir my_results/
```

### Output

```
╭─────────────────────────────────────────╮
│      Aggregate Statistics               │
│      Directory: output/                 │
╰─────────────────────────────────────────╯

Found 25 extraction files

Overall Statistics:

┌────────────────────────────┬─────────────────────┐
│ Metric                     │ Value               │
├────────────────────────────┼─────────────────────┤
│ Total Extractions          │ 25                  │
│ Successful                 │ 23 (92.0%)          │
│ Failed                     │ 2 (8.0%)            │
│                            │                     │
│ Average Confidence         │ 0.847               │
│ Min Confidence             │ 0.620               │
│ Max Confidence             │ 0.980               │
│                            │                     │
│ Total Tokens               │ 1,179,225           │
│ Avg Tokens/Extraction      │ 47,169              │
└────────────────────────────┴─────────────────────┘

Data Completeness:

┌────────────────────────────┬─────────────────────┐
│ Field                      │ Present             │
├────────────────────────────┼─────────────────────┤
│ Birth Date                 │ 23/25 (92.0%)       │
│ Death Date                 │ 25/25 (100.0%)      │
│ Promotions                 │ 20/25 (80.0%)       │
└────────────────────────────┴─────────────────────┘

Tool Usage:

┌─────────────────────────────────┬────────────────┐
│ Tool                            │ Count          │
├─────────────────────────────────┼────────────────┤
│ save_officer_bio                │ 48             │
│ verify_information_present      │ 92             │
│ validate_dates                  │ 23             │
│ lookup_existing_officer         │ 23             │
│ lookup_unit_by_name            │ 46             │
└─────────────────────────────────┴────────────────┘
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--dir` | No | Directory with extractions (default: output/) |

### Use Cases

- **Performance Review**: Track success rates over time
- **Quality Analysis**: Monitor confidence scores
- **Cost Tracking**: Calculate total token usage
- **Data Completeness**: Identify missing fields

---

## 7. interactive - Interactive Mode (NEW!)

REPL-style interface for quick testing and exploration.

### Basic Usage

```bash
python cli.py interactive
```

### Features

- ✅ **REPL Interface** - Type commands interactively
- ✅ **Quick Testing** - Test different obituaries instantly
- ✅ **Paste Support** - Paste obituary text directly
- ✅ **Real-time Feedback** - See confidence scores immediately
- ✅ **Session Statistics** - Track your work session
- ✅ **Command History** - Review what you've done
- ✅ **Colorful Output** - Rich formatted results

### Available Commands

#### 📋 Extraction Commands

| Command | Description |
|---------|-------------|
| `extract <url>` | Extract biography from URL |
| `paste` | Paste obituary text (multi-line) |
| `test` | Run test extraction on sample data |
| `batch <file>` | Batch process URLs from file |

#### 🔍 Analysis Commands

| Command | Description |
|---------|-------------|
| `validate <file>` | Re-validate saved extraction JSON |
| `replay <file>` | Replay conversation from extraction file |
| `search <query>` | Search output files by name/content |

#### 🛠️ System Commands

| Command | Description |
|---------|-------------|
| `run-tests` | Run comprehensive test suite |
| `demo` | Run full presentation demo |
| `config` | Show current configuration |
| `stats` | Show session statistics |
| `api-check` | Check Anthropic API connection |
| `db-check` | Check database connection |

#### 💡 Utility Commands

| Command | Description |
|---------|-------------|
| `history` | Show command history |
| `clear` | Clear screen |
| `help` | Show help message |
| `exit`, `quit`, `q` | Exit interactive mode |

### Interactive Session Example

```
╭─────────────────────────────────────────╮
│         Interactive Mode                │
│   REPL-style interface for quick        │
│          testing                        │
╰─────────────────────────────────────────╯

✓ SDK initialized - Ready for commands

Available Commands:
  extract <url>           - Extract from URL
  paste                   - Paste obituary text directly
  test                    - Run test extraction
  demo                    - Run full presentation demo
  stats                   - Show session statistics
  help                    - Show this help
  exit or quit            - Exit interactive mode

plAgent> help

Interactive Mode Commands:
┌─────────────────────────┬────────────────────────────────┐
│ Command                 │ Description                    │
├─────────────────────────┼────────────────────────────────┤
│ extract <url>           │ Extract biography from URL     │
│ paste                   │ Paste obituary text           │
│ test                    │ Run test extraction           │
│ demo                    │ Run full presentation demo    │
│ stats                   │ Show session statistics       │
│ help                    │ Show this help                │
│ exit, quit, q           │ Exit interactive mode         │
└─────────────────────────┴────────────────────────────────┘

plAgent> extract https://www.news.cn/obituary.html

Extracting from URL...
✓ Fetched 1,234 characters
Extracting biography (watch tool calls)...

✓ Extraction Successful!

┌──────────────────────┬─────────────────────┐
│ Name                 │ 林炳尧              │
│ Pinyin               │ Lín Bǐngyáo         │
│ Hometown             │ 福建省晋江市        │
│ Confidence           │ 0.85                │
│ Tokens Used          │ 47,169              │
│ Tool Calls           │ 9                   │
└──────────────────────┴─────────────────────┘

Saved to: output/林炳尧_20260211_160000.json

Suggested Actions:
  • High confidence - Ready for database
  • Validate: python cli.py validate --json output/林炳尧_20260211_160000.json
  • Replay: python cli.py replay --json output/林炳尧_20260211_160000.json

plAgent> test

Running test extraction...
✓ Loaded 1,234 characters
Extracting...

✓ Test passed: 林炳尧
  Confidence: 0.85
  Tokens: 47,169

plAgent> stats

Session Statistics:
┌──────────────────────────┬─────────────────────┐
│ Metric                   │ Value               │
├──────────────────────────┼─────────────────────┤
│ Total Extractions        │ 2                   │
│ Successful               │ 2                   │
│ Failed                   │ 0                   │
│ Success Rate             │ 100.0%              │
│ Total Tokens             │ 94,338              │
│ Avg Tokens/Extraction    │ 47,169              │
└──────────────────────────┴─────────────────────┘

plAgent> exit

Session Summary:
  Extractions: 2
  Successful: 2
  Total Tokens: 94,338

Goodbye!
```

### Paste Command

Paste obituary text directly for quick testing:

```
plAgent> paste

Paste obituary text (press Ctrl+D or Ctrl+Z when done):
Tip: You can paste multiple lines

林炳尧同志逝世
新华社北京1月15日电 原南京军区副司令员林炳尧同志，
于2023年1月15日在南京逝世，享年80岁。
...
[Press Ctrl+D]

✓ Received 1,234 characters

Extracting biography...

✓ Extraction Successful!

┌──────────────────────┬─────────────────────┐
│ Name                 │ 林炳尧              │
│ Confidence           │ 0.85                │
│ Tokens Used          │ 47,169              │
└──────────────────────┴─────────────────────┘
```

### Use Cases

#### Use Case 1: Quick Testing
```bash
# Start interactive mode
python cli.py interactive

# In the REPL:
plAgent> test
plAgent> extract https://www.news.cn/obituary.html
plAgent> stats
plAgent> exit
```

#### Use Case 2: Paste Multiple Obituaries
```bash
python cli.py interactive

plAgent> paste
[Paste obituary 1]
plAgent> paste
[Paste obituary 2]
plAgent> paste
[Paste obituary 3]
plAgent> stats
plAgent> exit
```

#### Use Case 3: Development/Debugging
```bash
python cli.py interactive

plAgent> test
plAgent> extract https://...
# Review results
plAgent> test
# Compare with another extraction
plAgent> stats
```

#### Use Case 4: Team Presentation
```bash
python cli.py interactive

# Run the full demo for your team
plAgent> demo

# This will launch the presentation demo with:
# - Live tool call monitoring
# - Control variable verification highlights
# - Color-coded confidence scoring
# - Database integration demo
# - Team integration points
# - Scalability projections

# Demo runs for 2-3 minutes automatically
# Press Enter when complete to return to interactive mode
```

#### Use Case 5: Complete Workflow
```bash
python cli.py interactive

# 1. Check system health
plAgent> api-check
✓ API Connection: SUCCESS

plAgent> db-check
✓ Database Connection: SUCCESS

# 2. Run tests
plAgent> run-tests --fast
✓ All tests passed!

# 3. Extract from URL
plAgent> extract https://www.news.cn/obituary.html
✓ Extraction Successful!

# 4. Validate the extraction
plAgent> validate output/林炳尧_20260212.json
✓ Schema Validation: PASSED

# 5. Replay to see how it worked
plAgent> replay output/林炳尧_20260212.json
[Shows tool call sequence]

# 6. Check session stats
plAgent> stats
Total Extractions: 1
Successful: 1

# 7. Search for officer
plAgent> search 林炳尧
Found 1 match(es):
  • 林炳尧_20260212.json

# 8. View configuration
plAgent> config
[Shows current settings]

# 9. Check history
plAgent> history
1. api-check
2. db-check
3. run-tests --fast
...

plAgent> exit
```

### Benefits

- **Fast Iteration** - No need to restart for each test
- **Easy Pasting** - Paste obituary text directly
- **Session Tracking** - See cumulative statistics
- **Immediate Feedback** - Confidence scores and suggestions
- **No Script Writing** - Interactive exploration
- **Development Friendly** - Great for debugging

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+C` | Cancel current command (doesn't exit) |
| `Ctrl+D` | End paste input / Exit (if at prompt) |
| `Ctrl+Z` | End paste input (Windows) |

### Tips

1. **Use `test` first** to verify SDK is working
2. **Use `paste` for quick tests** without needing URLs
3. **Use `demo` to showcase** the agent to your team (2-3 min presentation)
4. **Check `stats` regularly** to track your session
5. **Use `help` anytime** to see available commands
6. **Use `extract` for URLs** to fetch automatically

---

## Global Flags

Available for all commands:

| Flag | Description |
|------|-------------|
| `--verbose`, `-v` | Show detailed output |
| `--debug` | Show debug logs with tracebacks |
| `--config FILE` | Use alternative config file (not yet implemented) |

### Examples

```bash
# Verbose extraction
python cli.py extract --url "..." --verbose

# Debug batch processing
python cli.py batch --file urls.txt --debug

# Verbose test
python cli.py test --verbose
```

---

## Complete Examples

### Example 1: Basic Workflow

```bash
# 1. Test the system
python cli.py test

# 2. Extract from single URL
python cli.py extract --url "https://www.news.cn/obituary.html"

# 3. Validate the extraction
python cli.py validate --json output/林炳尧_20260211.json

# 4. View statistics
python cli.py stats
```

### Example 2: Batch Processing Workflow

```bash
# 1. Create URL file
cat > urls.txt << EOF
https://www.news.cn/obituary1.html
https://www.news.cn/obituary2.html
https://www.news.cn/obituary3.html
EOF

# 2. Process batch
python cli.py batch --file urls.txt --save-db

# 3. View statistics
python cli.py stats

# 4. Replay interesting extraction
python cli.py replay --json output/林炳尧_20260211.json
```

### Example 3: Debugging Workflow

```bash
# 1. Extract with verbose output
python cli.py extract --url "https://..." --verbose

# 2. If extraction seems wrong, replay it
python cli.py replay --json output/officer_20260211.json

# 3. Re-run validation
python cli.py validate --json output/officer_20260211.json

# 4. Test with similar obituary
python cli.py test --obituary data/similar_obituary.txt
```

---

## Error Handling

The CLI provides helpful error messages:

### File Not Found

```bash
$ python cli.py validate --json missing.json
✗ Error: File not found: missing.json
```

### Invalid URL

```bash
$ python cli.py extract --url "not-a-url"
✗ Error: Failed to fetch obituary from URL
```

### API Key Missing

```bash
$ python cli.py extract --url "https://..."
✗ Error: ANTHROPIC_API_KEY is required but not found in environment.

Please add it to your .env file:
  ANTHROPIC_API_KEY=your_key_here
```

### Debug Mode

```bash
# Get full traceback
python cli.py extract --url "..." --debug
```

---

## Integration with Other Scripts

The CLI is complementary to existing scripts:

| Script | CLI Equivalent |
|--------|----------------|
| `python demo_agentic_extraction.py` | `python cli.py test` |
| `python batch_test.py` | `python cli.py batch --file data/test_urls.txt` |
| `python batch_processor.py urls.txt` | `python cli.py batch --file urls.txt` |

**Advantage of CLI**: Single unified interface with consistent flags and output.

---

## Tips & Tricks

### 1. Quick Stats

```bash
# Quick overview of your extractions
python cli.py stats | grep -E "Successful|Average Confidence"
```

### 2. Batch with Logging

```bash
# Save all output to log file
python cli.py batch --file urls.txt --verbose 2>&1 | tee batch.log
```

### 3. Find Low Confidence

```bash
# List all extractions (including confidence scores)
python cli.py stats --dir output/

# Then manually check needs_review/
ls output/needs_review/
```

### 4. Test Different Models

```bash
# Edit .env to change MODEL_NAME
# Then test:
python cli.py test --verbose
```

### 5. Chain Commands

```bash
# Extract, validate, and show stats
python cli.py extract --url "https://..." && \
python cli.py validate --json output/latest.json && \
python cli.py stats
```

---

## Troubleshooting

### Command not found: python

Try `python3`:
```bash
python3 cli.py --help
```

### Import errors

Install dependencies:
```bash
pip install -r requirements.txt
```

### Slow batch processing

Increase rate limit:
```bash
python cli.py batch --file urls.txt --rate-limit 2.0
```

### Database errors

Use `--save-db` only if PostgreSQL is configured:
```bash
# Check .env has DATABASE_URL
cat .env | grep DATABASE_URL
```

---

## Next Steps

1. **Learn basics**: Start with `python cli.py test`
2. **Single extraction**: Try `python cli.py extract --url "..."`
3. **Batch processing**: Use `python cli.py batch --file urls.txt`
4. **Analysis**: Run `python cli.py stats` to see results
5. **Debugging**: Use `python cli.py replay` to understand extractions

---

## Reference

### Help Text

```bash
# Main help
python cli.py --help

# Command-specific help
python cli.py extract --help
python cli.py batch --help
python cli.py test --help
python cli.py validate --help
python cli.py replay --help
python cli.py stats --help
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error or failure |

---

Generated: 2026-02-11
