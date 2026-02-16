# Testing Guide

Testing supports confidence in extraction quality, validation behavior, and integrations.

## Quick Start

```bash
python run_all_tests.py
```

Reports:

- `output/reports/test_results.html`
- `output/reports/test_results.json`

## Useful Commands

```bash
python run_all_tests.py --fast
python run_all_tests.py --verbose
python run_all_tests.py --category unit
python run_all_tests.py --category validation
python run_all_tests.py --category integration
python run_all_tests.py --category batch
python run_all_tests.py --ci
```

## Test Areas

- Unit: schema/config/registry behavior
- Validation: date + evidence verification tools
- Integration: SDK extraction flow + Anthropic interface
- Batch: multi-URL processing and reporting

## Direct Pytest Examples

```bash
python -m pytest -q
python -m pytest -q tests/test_validation_tools.py
python -m pytest -q tests/test_agent.py
python -m pytest -q tests/test_batch_processor.py
```

## CI Notes

- `--ci` provides stricter exit-code behavior and compact output.
- Integration tests require `ANTHROPIC_API_KEY`.
- Some tests may skip when API/database prerequisites are absent.

## Troubleshooting

- Missing API key: set `ANTHROPIC_API_KEY` in `.env`
- Missing DB credentials: skip DB-dependent paths or configure DB vars
- Slow runs: use `--fast` during local iteration
- Missing HTML report: ensure `pytest-html` is installed
