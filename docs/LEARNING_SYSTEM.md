# Learning System Guide

The learning system adds few-shot examples from prior successful extractions to improve consistency.

## Runtime Notes

- Extraction runtime is single-pass.
- Few-shot behavior is controlled by:
  - `ENABLE_FEW_SHOT_SINGLE_PASS`
  - `PLAgentSDK(use_few_shot=...)`

## How It Works

1. Load successful extraction JSON files from `output/`.
2. Filter by confidence threshold.
3. Select a small, diverse subset of examples.
4. Append examples to the extraction system prompt.

## Quick Usage

```python
from agent import PLAgentSDK

sdk = PLAgentSDK(use_few_shot=True)
result = sdk.extract_bio_agentic(source_text=source_text, source_url=source_url)
```

Disable explicitly:

```python
sdk = PLAgentSDK(use_few_shot=False)
```

## Learner API

```python
from learning_system import ExtractionLearner

learner = ExtractionLearner(examples_dir="output/")
stats = learner.get_statistics()
examples = learner.get_few_shot_examples(n=3, min_confidence=0.8, diversity=True)
enhanced_prompt = learner.add_to_system_prompt(base_prompt, examples)
```

## Operational Guidance

- Start collecting examples before enabling in production.
- Use high-confidence examples only (`>= 0.8` recommended).
- Keep example count small (2-3) to avoid prompt bloat.
- Re-check token usage after enabling few-shot.

## Validation

```bash
python learning_system.py
```

## Troubleshooting

- Few-shot not active:
  - verify enough successful examples exist
  - check `ENABLE_FEW_SHOT_SINGLE_PASS`
  - ensure output files are valid extraction JSON

- Token usage increased too much:
  - reduce `n` examples
  - raise `min_confidence`
  - disable few-shot for cost-sensitive runs
