# CLI Guide - PLA Agent SDK

This guide documents the supported public CLI surface.

## Supported Commands

- `extract` - extract one biography from a URL
- `batch` - process multiple URLs from a file
- `validate` - validate a saved extraction JSON file
- `interactive` - REPL workflow for exploratory use

## 1. extract

```bash
python cli.py extract --url https://www.news.cn/.../c.html
python cli.py extract --url https://www.news.cn/.../c.html --save-db
```

## 2. batch

```bash
python cli.py batch --file urls.txt
python cli.py batch --file urls.txt --save-db
python cli.py batch --file urls.txt --rate-limit 2.0
```

## 3. validate

```bash
python cli.py validate --json output/officer_20260216_120000.json
```

## 4. interactive

```bash
python cli.py interactive
```

## Notes

- Extraction runs in universal mode; source adaptation is automatic.
- Default extraction mode is `single_pass` (single extraction pass + local validation + gated verification).
- Deprecated commands (`test`, `replay`, `stats`, `batch-test`, `batch-files`) were removed from the public CLI.
- For command options, use `python cli.py <command> --help`.
