# plAgent

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![Model](https://img.shields.io/badge/Claude-Sonnet%204.6-7B61FF)](https://www.anthropic.com/)

Structured extraction of PLA officer biographical data from Chinese-language sources (obituaries, news, wiki-style pages, and similar documents).

The current runtime is **single-pass only**: one model extraction call, local validation, and selective evidence verification for risky fields.

## Why This Project

This SDK is designed for teams that need reproducible, structured biographical data instead of manual copy/paste from unstructured text.

It prioritizes:

- extraction quality (schema + date validation)
- anti-hallucination safeguards (selective source verification)
- operational throughput (batch processing + rate limits)
- optional persistence to PostgreSQL

## Key Features

- Single-pass JSON extraction flow
- Source-adaptive behavior across mixed content types
- Validation tools:
  - `save_officer_bio` schema/type enforcement
  - `validate_dates` chronology checks
  - `verify_information_present` source-evidence checks
- Batch processing and review queues
- Interactive CLI mode for exploration/debugging
- Built-in test runner with HTML/JSON reports

## How It Works

1. Fetch source text from URL/file/paste input.
2. Run one extraction call to Claude.
3. Validate schema and dates locally.
4. Verify only suspicious high-risk fields against registered source context.
5. Save result to JSON (and optionally DB if enabled/confident).

Typical runtime profile:

- `conversation_turns`: usually `1` (occasionally `2` for repair)
- `tool_calls`: usually `2-4`
- token usage: typically in low thousands for normal-length pages

## Installation

### 1. Clone and enter project

```bash
cd "pla-agent-sdk"
```

### 2. Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Configuration

Create `.env` in project root:

```bash
# Required
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional database
DATABASE_URL=postgresql://user:password@localhost:5432/pla_leadership
# or DB_HOST / DB_NAME / DB_USER / DB_PASSWORD / DB_PORT

# Optional runtime tuning
MODEL_NAME=claude-sonnet-4-6
LOG_LEVEL=INFO
MAX_VERIFY_CALLS_PER_EXTRACTION=2
ENABLE_FEW_SHOT_SINGLE_PASS=false
TOKEN_BUDGET_TARGET_AVG=15000
```

## Quick Start

### Extract one URL

```bash
python cli.py extract --url "https://www.news.cn/.../c.html"
```

### Extract and save high-confidence results to DB

```bash
python cli.py extract --url "https://www.news.cn/.../c.html" --save-db
```

### Batch process URLs from file

```bash
python cli.py batch --file urls.txt
python cli.py batch --file urls.txt --save-db --rate-limit 2.0
```

`urls.txt` format:

```text
https://www.news.cn/2025/obituary1.html
https://www.news.cn/2025/obituary2.html
# comments allowed
```

### Re-validate saved extraction JSON

```bash
python cli.py validate --json output/officer_20260216_120000.json
```

### Interactive mode

```bash
python cli.py interactive
```

## CLI Reference

```bash
python cli.py --help
python cli.py extract --help
python cli.py batch --help
python cli.py validate --help
python cli.py interactive --help
```

## Outputs

- `output/*.json` - extraction results
- `output/needs_review/*.json` - low-confidence/failed items for manual review
- `output/reports/test_results.html` - test report (HTML)
- `output/reports/test_results.json` - test report (JSON)

## Testing

### Run full suite

```bash
python run_all_tests.py
```

### Useful options

```bash
python run_all_tests.py --fast
python run_all_tests.py --verbose
python run_all_tests.py --category unit
python run_all_tests.py --category validation
python run_all_tests.py --category integration
python run_all_tests.py --category batch
python run_all_tests.py --ci
```

### Run pytest directly

```bash
python -m pytest -q
python -m pytest -q tests/test_validation_tools.py
python -m pytest -q tests/test_agent.py
```

## Project Structure

```text
pla-agent-sdk/
├── agent.py
├── cli.py
├── batch_processor.py
├── config.py
├── schema.py
├── fetch_source.py
├── learning_system.py
├── tools/
├── tests/
├── docs/
├── data/
├── output/
└── run_all_tests.py
```

## Troubleshooting

### `ANTHROPIC_API_KEY` missing

Set `ANTHROPIC_API_KEY` in `.env`.

### Database errors

If DB is optional for your run, omit `--save-db`.

### High token usage

- check source length
- inspect extraction notes for repair/verification retries
- consider `PLAgentSDK(use_few_shot=False)` if needed

### Rate limiting (`429`)

Increase batch delay:

```bash
python cli.py batch --file urls.txt --rate-limit 3.0
```

## Documentation

See `docs/` for focused guides:

- `docs/WORKFLOW_GUIDE.md`
- `docs/CLI_GUIDE.md`
- `docs/CONFIGURATION_GUIDE.md`
- `docs/VALIDATION_TOOLS_GUIDE.md`
- `docs/TESTING_GUIDE.md`

## Notes on Legacy Compatibility

- Public runtime is single-pass only.
- Python compatibility parameters for historical mode inputs are accepted but ignored with warnings.
