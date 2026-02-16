# Workflow Guide

This project now runs a **single extraction workflow**.

## Single-Pass Workflow

1. One Claude extraction call (JSON target output)
2. `save_officer_bio` schema/type validation
3. `validate_dates` chronology check
4. `verify_information_present` only for suspicious rare fields
5. optional `save_to_database`

Expected runtime characteristics:

- `conversation_turns`: usually `1`, sometimes `2` (repair pass)
- `tool_calls`: usually `2-4`
- token cost: significantly lower than historical multi-turn patterns

## CLI Examples

```bash
python cli.py extract --url "https://www.news.cn/.../c.html"
python cli.py batch --file urls.txt
```

## Workflow Testing

```bash
python run_all_tests.py
```
