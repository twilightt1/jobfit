# Technical Architecture

JobFit AI is implemented as a split frontend/backend AI application:

```text
frontend/  Next.js UI
backend/   Python FastAPI API + AI/ML pipeline
```

Core AI architecture:

1. Schema-first LLM extraction.
2. Skill normalization and alias matching.
3. Embedding-based semantic evidence retrieval.
4. Deterministic explainable scoring.
5. Grounded resume rewrite generation.
6. Truth guard classification.
7. AI run logging and evaluation.
