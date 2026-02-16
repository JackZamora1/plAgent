# Batch Processing Guide

Batch processing is available via:

```bash
python cli.py batch --file urls.txt
```

## Common Commands

```bash
python cli.py batch --file urls.txt
python cli.py batch --file urls.txt --save-db
python cli.py batch --file urls.txt --rate-limit 2.0
```

## Input Format

One URL per line, with optional blank lines and `#` comments.

```text
https://www.news.cn/2025/obituary1.html
https://www.news.cn/2025/obituary2.html
# comment
https://www.news.cn/2025/obituary3.html
```

## Outputs

- `output/*.json`: extraction files
- `output/needs_review/*.json`: low-confidence or failed extractions
- `output/batch_report_*.txt`: batch summary report
- `output/logs/*`: batch/extraction logs

## Operational Notes

- Runtime is single-pass by default.
- Review threshold is profile-driven (`universal` profile threshold).
- Increase `--rate-limit` when API throttling appears.
