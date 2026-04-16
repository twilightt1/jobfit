# Prompt Design

Prompts are stored under:

```text
backend/app/ai/prompts/
```

P0 prompt files:

- `resume_parser.v1.md`
- `job_parser.v1.md`
- `match_explainer.v1.md`
- `resume_optimizer.v1.md`
- `truth_guard.v1.md`
- `json_repair.v1.md`

All structured prompts should return JSON only and be validated with Pydantic schemas.
