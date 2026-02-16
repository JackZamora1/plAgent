# Schema Guide

Schema validation is enforced in the single-pass extraction pipeline.

## Core Models

- `OfficerBio`: structured output fields
- `ToolResult`: tool execution result contract
- `AgentExtractionResult`: extraction metadata + output container

## Validation Highlights

- strict field typing via Pydantic
- date format constraints (`YYYY` or `YYYY-MM-DD`)
- required core fields (`name`, `source_url`)
- confidence score bounds

Use schema validation in tests and CLI re-validation (`python cli.py validate --json ...`).
