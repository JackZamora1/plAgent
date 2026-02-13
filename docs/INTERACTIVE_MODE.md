# Interactive Mode - Quick Guide

REPL-style interface for quick testing and exploration.

## 🚀 Quick Start

```bash
python cli.py interactive
```

---

## 🎯 What is Interactive Mode?

A **Read-Eval-Print Loop (REPL)** interface that lets you:
- Test extractions instantly
- Paste obituary text directly
- See results in real-time
- Track session statistics
- No script writing needed

**Perfect for:**
- 🧪 Quick testing
- 🐛 Debugging extractions
- 📚 Learning the system
- 🔄 Iterative development

---

## 📝 Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `extract <url>` | Extract from URL | `extract https://www.news.cn/...` |
| `paste` | Paste obituary text | `paste` (then paste text) |
| `test` | Run test extraction | `test` |
| `stats` | Show session stats | `stats` |
| `help` | Show help | `help` |
| `exit` / `quit` / `q` | Exit | `exit` |

---

## 💡 Example Session

### Session 1: Quick Test

```
$ python cli.py interactive

╭─────────────────────────────────────────╮
│         Interactive Mode                │
╰─────────────────────────────────────────╯

✓ SDK initialized - Ready for commands

plAgent> test

Running test extraction...
✓ Loaded 1,234 characters
✓ Test passed: 林炳尧
  Confidence: 0.85
  Tokens: 47,169

plAgent> exit

Session Summary:
  Extractions: 1
  Successful: 1
  Total Tokens: 47,169

Goodbye!
```

---

### Session 2: Extract from URL

```
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
```

---

### Session 3: Paste Obituary Text

```
plAgent> paste

Paste obituary text (press Ctrl+D or Ctrl+Z when done):
Tip: You can paste multiple lines

林炳尧同志逝世
新华社北京1月15日电 原南京军区副司令员林炳尧同志，
于2023年1月15日在南京逝世，享年80岁。

林炳尧是福建晋江人，1961年入伍，1964年加入中国共产党。
历任战士、班长、排长、连长等职。1995年晋升少将军衔。

[Press Ctrl+D or Ctrl+Z]

✓ Received 234 characters

Extracting biography...

✓ Extraction Successful!

┌──────────────────────┬─────────────────────┐
│ Name                 │ 林炳尧              │
│ Confidence           │ 0.85                │
│ Tokens Used          │ 45,123              │
└──────────────────────┴─────────────────────┘

Saved to: output/林炳尧_20260211_160030.json
```

---

### Session 4: View Statistics

```
plAgent> stats

Session Statistics:
┌──────────────────────────┬─────────────────────┐
│ Metric                   │ Value               │
├──────────────────────────┼─────────────────────┤
│ Total Extractions        │ 3                   │
│ Successful               │ 3                   │
│ Failed                   │ 0                   │
│ Success Rate             │ 100.0%              │
│ Total Tokens             │ 139,461             │
│ Avg Tokens/Extraction    │ 46,487              │
└──────────────────────────┴─────────────────────┘
```

---

## 🎨 Features

### 1. Real-Time Feedback

See extraction results immediately with:
- ✅ Confidence scores
- ✅ Token usage
- ✅ Tool calls count
- ✅ Suggested next actions

### 2. Paste Support

Paste obituary text directly:
```
plAgent> paste
[Paste your text]
[Press Ctrl+D]
```

**Perfect for:**
- Testing scraped content
- Debugging specific obituaries
- Quick experiments

### 3. Session Tracking

Track your work with `stats`:
- Total extractions
- Success rate
- Token usage
- Average efficiency

### 4. Colorful Output

Rich formatting with:
- 🟢 Green for success
- 🔴 Red for errors
- 🟡 Yellow for warnings
- 📊 Tables for data

### 5. Smart Suggestions

After each extraction, get:
- Quality assessment (high/low confidence)
- Next action recommendations
- Validation commands
- Replay commands

---

## 🔧 Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+C` | Cancel current command (stay in REPL) |
| `Ctrl+D` | End paste input / Exit REPL |
| `Ctrl+Z` | End paste input (Windows) |
| Type `exit` | Clean exit with summary |

---

## 💡 Use Cases

### Use Case 1: Quick Testing

```bash
python cli.py interactive

plAgent> test
# Verify system works

plAgent> extract https://www.news.cn/obituary.html
# Test with real URL

plAgent> stats
# Check results

plAgent> exit
```

---

### Use Case 2: Debugging

```bash
python cli.py interactive

plAgent> paste
[Paste problematic obituary]

plAgent> paste
[Paste working obituary]

plAgent> stats
# Compare results

plAgent> exit
```

---

### Use Case 3: Batch Testing

```bash
python cli.py interactive

plAgent> extract https://www.news.cn/obituary1.html
plAgent> extract https://www.news.cn/obituary2.html
plAgent> extract https://www.news.cn/obituary3.html

plAgent> stats
# Review batch results

plAgent> exit
```

---

### Use Case 4: Development

```bash
python cli.py interactive

plAgent> test
# Test before changes

# [Make code changes]

plAgent> test
# Test after changes

plAgent> stats
# Compare token usage

plAgent> exit
```

---

## 🆚 Interactive vs Other Modes

| Feature | Interactive | extract | batch |
|---------|-------------|---------|-------|
| **Speed** | Instant | Single | Automated |
| **Flexibility** | High | Medium | Low |
| **Paste Support** | ✅ Yes | ❌ No | ❌ No |
| **Session Stats** | ✅ Yes | ❌ No | ✅ Yes |
| **URL Fetching** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Best For** | Testing | Production | Bulk |

---

## ⚡ Pro Tips

### 1. Start with Test

Always run `test` first to verify setup:
```
plAgent> test
```

### 2. Use Paste for Quick Experiments

Paste text directly instead of creating files:
```
plAgent> paste
[Paste text]
```

### 3. Check Stats Regularly

Track your progress:
```
plAgent> stats
```

### 4. Use Help Anytime

Forgot a command?
```
plAgent> help
```

### 5. Exit Cleanly

Use `exit` to see session summary:
```
plAgent> exit

Session Summary:
  Extractions: 5
  Successful: 5
  Total Tokens: 235,845
```

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'rich'"

Install Rich:
```bash
pip install rich
```

### Paste not working

**Mac/Linux**: Press `Ctrl+D` to end input
**Windows**: Press `Ctrl+Z` then Enter

### Can't exit

Type `exit` or `quit`, or press `Ctrl+D` at prompt

### Want to cancel command

Press `Ctrl+C` (doesn't exit REPL)

---

## 📊 Example Workflow

### Research Workflow

```
1. Start: python cli.py interactive
2. Test: plAgent> test
3. Extract: plAgent> extract <url>
4. Review: Check confidence score
5. Validate: Use suggested command
6. Repeat: Try another URL
7. Stats: plAgent> stats
8. Exit: plAgent> exit
```

### Development Workflow

```
1. Start: python cli.py interactive
2. Baseline: plAgent> test
3. [Make changes to code]
4. Test: plAgent> test
5. Compare: plAgent> stats
6. Iterate: Repeat 3-5
7. Exit: plAgent> exit
```

---

## ✅ When to Use Interactive Mode

**Use interactive mode when:**
- 🧪 Testing the system
- 🐛 Debugging extractions
- 📝 Pasting obituary text
- 🔄 Trying multiple URLs
- 📊 Tracking session work
- 🎓 Learning the SDK

**Use other modes when:**
- 📦 Processing many URLs → `batch`
- 🤖 Automated pipelines → `extract`
- 📈 Analyzing results → `stats`
- 🔍 Reviewing extraction → `replay`

---

## 🎓 Learning Path

### Beginner
```
1. python cli.py interactive
2. plAgent> help
3. plAgent> test
4. plAgent> exit
```

### Intermediate
```
1. python cli.py interactive
2. plAgent> test
3. plAgent> extract <url>
4. plAgent> stats
5. plAgent> exit
```

### Advanced
```
1. python cli.py interactive
2. plAgent> paste
   [Paste custom text]
3. plAgent> extract <url1>
4. plAgent> extract <url2>
5. plAgent> stats
6. plAgent> exit
```

---

## 🚀 Getting Started

### Step 1: Launch

```bash
python cli.py interactive
```

### Step 2: Test

```
plAgent> test
```

### Step 3: Explore

```
plAgent> help
```

### Step 4: Extract

```
plAgent> extract <url>
```
or
```
plAgent> paste
[Paste text]
```

### Step 5: Review

```
plAgent> stats
```

### Step 6: Exit

```
plAgent> exit
```

---

## 📚 See Also

- **CLI_GUIDE.md** - Complete CLI reference
- **CLI_README.md** - CLI quick start
- **README.md** - Overall SDK documentation

---

Generated: 2026-02-11
