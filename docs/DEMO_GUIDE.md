# Demo Guide

This guide helps you run and present the CLI demo flow cleanly.

## Run Demo

```bash
source .venv/bin/activate
python scripts/demo.py
```

## Recommended Setup

- maximize terminal window
- increase font size for visibility
- verify `ANTHROPIC_API_KEY` is set
- test once before presenting

## Suggested Talk Track

1. Show raw source text input.
2. Run extraction and highlight structured output.
3. Explain validation and selective verification.
4. Show confidence, tokens, and saved output files.
5. Mention optional DB integration and batch scaling.

## Common Q&A

- **Accuracy:** focus on core-field correctness + validation safeguards.
- **Cost:** single-pass significantly reduces token usage vs historical multi-turn behavior.
- **Database:** optional; JSON outputs still work without DB.

## Troubleshooting

- API issues: verify `.env` key and network access
- rate limits: increase batch `--rate-limit`
- rendering issues: check terminal color/font settings

## Related Commands

```bash
python cli.py --help
python cli.py extract --url "https://..."
python cli.py batch --file urls.txt
python cli.py interactive
```
