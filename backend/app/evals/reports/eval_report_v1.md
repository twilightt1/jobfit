# Evaluation Report (v1)

- Requested task: `matching`
- Generated at: `2026-06-18T08:58:41.733209+00:00`
- Persisted run id: `not_persisted`

## Warnings

- LLM judge skipped: AI_PROVIDER must be 'openai'.
- Local embedding runtime unavailable; using deterministic eval embeddings: No module named 'sentence_transformers'

## Matching engine

Average latency: `0.66 ms`

| Metric | Value | Description |
| --- | --- | --- |
| `matched_skill_precision` | `100.0%` | Precision for the skills the match engine claims are covered. |
| `matched_skill_recall` | `100.0%` | Recall for expected matched skills. |
| `matched_skill_f1` | `100.0%` | Balanced score for matched-skill quality. |
| `missing_skill_precision` | `100.0%` | Precision for the skills the engine flags as missing. |
| `missing_skill_recall` | `100.0%` | Recall for expected missing skills. |
| `missing_skill_f1` | `100.0%` | Balanced score for missing-skill quality. |
| `semantic_match_precision` | `0.0%` | Precision for semantic or hybrid evidence against labeled semantic matches. |
| `semantic_match_recall` | `0.0%` | Recall for labeled semantic matches recovered by the match evidence. |
| `semantic_match_f1` | `0.0%` | Balanced semantic evidence quality score. |
| `score_band_accuracy` | `100.0%` | How often the deterministic score lands in the expected band. |
| `score_in_range_rate` | `0.0%` | How often the score lands inside the labeled calibration range. |
| `average_score_delta` | `10.00` | Average absolute distance from the target score range or band anchor. |

### Example outcomes

- **frontend_midlevel__react_typescript_mid** — `pass` — Computed score `80` with predicted band `strong_match`.
