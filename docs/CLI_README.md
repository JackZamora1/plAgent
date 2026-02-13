# Command-Line Interface - Quick Start

Unified CLI for PLA Agent SDK operations.

## 🎯 What is the CLI?

A single command-line tool that provides access to all SDK features:
- ✅ Single URL extraction
- ✅ Batch processing
- ✅ Test suite
- ✅ Validation
- ✅ Conversation replay
- ✅ Statistics analysis

## 🚀 Quick Start

### Step 1: Verify Installation

```bash
cd "/Users/jack/Documents/Documents/College Stuff/Clubs/2025-26/Concord Group/PLA Data Project/pla-agent-sdk"

# Install Rich if not already installed
pip install rich
```

### Step 2: Test the CLI

```bash
# Show help
python cli.py --help

# Or use python3
python3 cli.py --help
```

### Step 3: Run Test Suite

```bash
python cli.py test
```

Expected output:
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

---

## 📋 Available Commands

### 0. interactive - REPL Mode (NEW! ⭐)

```bash
python cli.py interactive
```

**Features:**
- Interactive REPL interface
- Commands: `extract <url>`, `paste`, `test`, `stats`, `help`, `exit`
- Paste obituary text directly
- Real-time feedback and suggestions
- Session statistics tracking

**Great for:**
- Quick testing
- Development/debugging
- Trying different obituaries
- Learning the system

---

### 1. extract - Single URL

```bash
python cli.py extract --url "https://www.news.cn/obituary.html"
```

**Options:**
- `--save-db` — Save to database if confidence ≥ 0.7
- `--verbose` — Show detailed conversation

**Example:**
```bash
python cli.py extract \
  --url "https://www.news.cn/obituary.html" \
  --save-db \
  --verbose
```

---

### 2. batch - Multiple URLs

```bash
python cli.py batch --file urls.txt
```

**Options:**
- `--save-db` — Save high-confidence results to DB
- `--rate-limit N` — Seconds between requests (default: 1.0)
- `--parallel N` — Workers (not yet implemented)

**Example:**
```bash
python cli.py batch \
  --file urls.txt \
  --save-db \
  --rate-limit 2.0
```

---

### 3. test - Test Suite

```bash
python cli.py test
```

**Options:**
- `--obituary FILE` — Use custom test file

**Example:**
```bash
python cli.py test --obituary data/my_test.txt
```

---

### 4. validate - Re-validate

```bash
python cli.py validate --json output/林炳尧_20260211.json
```

Checks:
- Required fields
- Date formats
- Confidence score
- Promotions data

---

### 5. replay - Conversation

```bash
python cli.py replay --json output/林炳尧_20260211.json
```

Shows:
- Tool call sequence
- Timestamps
- Success/failure status
- Extracted data (formatted JSON)

---

### 6. stats - Analytics

```bash
python cli.py stats
```

**Options:**
- `--dir PATH` — Directory to analyze (default: output/)

**Shows:**
- Success/failure rates
- Average confidence
- Token usage
- Data completeness
- Tool usage breakdown
- Common errors

**Example:**
```bash
python cli.py stats --dir output/
```

---

## 🎨 Rich Output Features

The CLI uses the Rich library for beautiful output:

✅ **Colored text** - Errors in red, success in green, warnings in yellow
✅ **Tables** - Formatted data display
✅ **Panels** - Boxed headers and summaries
✅ **Progress bars** - Real-time progress (in batch mode)
✅ **Syntax highlighting** - JSON with colors
✅ **Icons** - ✓ for success, ✗ for failure, ⚠ for warnings

---

## 🔧 Global Flags

Available for all commands:

### --verbose (-v)
Show detailed output:
```bash
python cli.py extract --url "..." --verbose
```

### --debug
Show debug logs with full tracebacks:
```bash
python cli.py batch --file urls.txt --debug
```

### --config (Future)
Use alternative config file:
```bash
python cli.py extract --url "..." --config custom.env
```

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| **CLI_GUIDE.md** | Complete command reference with examples |
| **CLI_README.md** | This quick start guide |
| **README.md** | Overall SDK documentation |

---

## 💡 Common Use Cases

### Use Case 1: Quick Test

```bash
# Test the system works
python cli.py test

# If passed, try single extraction
python cli.py extract --url "https://www.news.cn/obituary.html"
```

### Use Case 2: Batch Processing

```bash
# Create URL file
cat > urls.txt << EOF
https://www.news.cn/obituary1.html
https://www.news.cn/obituary2.html
https://www.news.cn/obituary3.html
EOF

# Process
python cli.py batch --file urls.txt --save-db

# Check results
python cli.py stats
```

### Use Case 3: Debug Extraction

```bash
# Extract with verbose output
python cli.py extract --url "..." --verbose

# Replay the conversation
python cli.py replay --json output/latest.json

# Validate the result
python cli.py validate --json output/latest.json
```

### Use Case 4: Quality Analysis

```bash
# Process batch
python cli.py batch --file urls.txt

# Analyze results
python cli.py stats

# Check specific extraction
python cli.py validate --json output/officer.json
```

---

## 🆚 CLI vs Other Scripts

| Task | Old Way | CLI Way |
|------|---------|---------|
| Test | `python demo_agentic_extraction.py` | `python cli.py test` |
| Batch | `python batch_processor.py urls.txt` | `python cli.py batch --file urls.txt` |
| Stats | Manual analysis | `python cli.py stats` |
| Validate | N/A | `python cli.py validate --json FILE` |
| Replay | N/A | `python cli.py replay --json FILE` |

**Advantages:**
- Unified interface
- Consistent flags
- Better error messages
- Rich output
- Built-in help

---

## 🐛 Troubleshooting

### ModuleNotFoundError: No module named 'rich'

```bash
pip install rich
```

### Command 'python' not found

Use `python3`:
```bash
python3 cli.py --help
```

### ANTHROPIC_API_KEY error

Add to `.env`:
```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
```

### File not found errors

Check paths:
```bash
# For extract
python cli.py extract --url "..." --verbose

# For batch
ls urls.txt  # Verify file exists

# For validate/replay
ls output/*.json  # Find the file
```

### Slow batch processing

Increase rate limit:
```bash
python cli.py batch --file urls.txt --rate-limit 2.0
```

---

## 📖 Getting Help

### General Help

```bash
python cli.py --help
```

### Command-Specific Help

```bash
python cli.py extract --help
python cli.py batch --help
python cli.py test --help
python cli.py validate --help
python cli.py replay --help
python cli.py stats --help
```

### Detailed Documentation

See **CLI_GUIDE.md** for:
- Complete command reference
- All options and flags
- More examples
- Advanced usage
- Tips & tricks

---

## ✅ Verification Checklist

Before using in production:

- [ ] `pip install rich` completed
- [ ] `python cli.py --help` works
- [ ] `python cli.py test` passes all tests
- [ ] `.env` has ANTHROPIC_API_KEY
- [ ] Test extraction works: `python cli.py extract --url "..."`
- [ ] Stats command works: `python cli.py stats`

---

## 🎓 Learning Path

### Beginner

1. Run help: `python cli.py --help`
2. Run test: `python cli.py test`
3. Check stats: `python cli.py stats`

### Intermediate

1. Extract single URL: `python cli.py extract --url "..."`
2. Validate result: `python cli.py validate --json output/officer.json`
3. Replay conversation: `python cli.py replay --json output/officer.json`

### Advanced

1. Batch processing: `python cli.py batch --file urls.txt --save-db`
2. Debug with verbose: `python cli.py extract --url "..." --verbose --debug`
3. Analyze all results: `python cli.py stats --dir output/`

---

## 🚀 Next Steps

1. **Install Rich**: `pip install rich`
2. **Test CLI**: `python cli.py test`
3. **Read guide**: Open CLI_GUIDE.md for full reference
4. **Try commands**: Start with `extract` or `test`
5. **Scale up**: Move to `batch` for multiple URLs

---

Generated: 2026-02-11
