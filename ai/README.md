# Waypoint AI — Prompts and Retrieval

This directory contains the AI/ML components of Waypoint.

## Structure

```
ai/
├── prompts/           # System prompts and template strings
│   └── system.py      # All prompt templates for NVIDIA NIM
├── retrieval/         # Data retrieval and grounding logic
│   └── grounding.py   # Ensures LLM output is grounded in DB facts
└── README.md
```

## Design principles

1. **The LLM never computes prices.** All money is handled by `Decimal` and `BudgetGuard` in code.
2. **Deterministic fallback.** If no API key is configured or the external service fails, Waypoint uses grounded template reasoning in 4 languages.
3. **Grounded explanations.** Every LLM output references actual data from `PS-04.db` — package names, component titles, guide names, prices — never hallucinated values.

## Supported languages

- English (`en-IN`)
- Hindi (`hi`)
- Tamil (`ta`)
- Telugu (`te`)

## Model

- **Provider**: NVIDIA NIM (OpenAI-compatible API)
- **Model**: `meta/llama-3.1-70b-instruct`
- **Fallback**: Deterministic multilingual templates (zero external dependency)
