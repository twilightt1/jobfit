# JobFit AI — AI Resume Match & Optimization Product Demo

JobFit AI is a product-style AI engineering project that turns a resume and a job description into an explainable match report, evidence-backed gaps, ATS keyword coverage, and truth-guarded resume rewrite suggestions.

It is intentionally scoped as a **portfolio/CV-ready product demo**, not a full SaaS platform. The goal is to demonstrate end-to-end AI product engineering: practical document ingestion, schema-first extraction, hybrid semantic/lexical scoring, AI safety guardrails, observability foundations, and a polished Next.js user experience.

## Product Story

Most resume tools produce generic feedback or rewrite text without proving whether the candidate actually has the underlying experience. JobFit AI focuses on a safer workflow:

1. Accept real-world resume/JD inputs.
2. Extract structured signals from both sides.
3. Score the fit with transparent evidence rows.
4. Highlight strengths, gaps, and missing ATS keywords.
5. Suggest resume improvements while flagging unsupported claims.
6. Present the result in a shareable report page.

## Demo Flow

```text
Open /analyze
  -> use the built-in EN/VI/ZH/JA demo data or upload real files
  -> submit the no-account analysis flow
  -> backend runs ingest -> parse -> match -> optimize -> truth guard
  -> open /reports/{id}
  -> share or export the report as Markdown
```

Main frontend routes:

- `/` — product landing page
- `/analyze` — no-account CV/JD analysis workbench
- `/reports/{id}` — shareable report detail page
- `/diagnostics` — AI pipeline/observability explainer page

## Key Features

| Area | What it demonstrates |
| --- | --- |
| Document ingestion | Resume/JD input via pasted text, PDF, DOCX, TXT, Markdown, or public JD URL |
| Explainable scoring | Hybrid semantic + lexical skill/requirement/experience/language breakdown with persisted evidence rows |
| Language support | English, Vietnamese, Chinese, and Japanese detection for resume/JD language matching |
| Resume optimization | Rewrite suggestions tied to match gaps and estimated score lift |
| Truth guard | Suggestions classified as `safe`, `needs_review`, or `unsupported` to avoid invented claims |
| Product UX | Polished landing page, live analyze workflow, sticky report actions, markdown export |
| AI observability | AI run/output tables, parse diagnostics, provider/model/repair metadata, embedding metadata |
| Evaluation foundation | Smoke datasets and CLI runner for parser, matching, semantic retrieval, and truth-guard checks |

## Architecture

```text
frontend/  Next.js 14 App Router product UI
backend/   FastAPI API, ingestion services, AI pipeline, scoring, guardrails
backend/app/db/  SQLAlchemy models for resumes, jobs, reports, evidence, AI runs, evals
infra/     Dockerfiles, Docker Compose, pgvector init script
docs/      PRD, architecture, prompt/eval docs, case study, CV summary
```

Runtime flow:

```text
Next.js /analyze
  -> POST /api/analyze multipart form
  -> ingestion layer extracts file/text/url content
  -> configured parser creates resume/job structured JSON
  -> embedding service indexes resume bullets + job skills/requirements
  -> hybrid match engine creates MatchReport + MatchEvidence
  -> optimizer creates RewriteSuggestion rows
  -> truth guard labels suggestion safety
  -> Next.js /reports/{id} reads and presents the final report
```

## Tech Stack

| Layer | Stack |
| --- | --- |
| Frontend | Next.js 14 App Router, React 18, TypeScript, vanilla CSS |
| Backend | FastAPI, SQLAlchemy 2 async, Pydantic, Alembic |
| Database | PostgreSQL 16, pgvector embeddings, JSONB report storage |
| AI pipeline | Local deterministic fallback by default, OpenAI-compatible LLM abstraction, local sentence-transformer embeddings |
| Ingestion | PDF/DOCX/TXT extraction, SSRF-aware public URL fetcher |
| Quality | GitHub Actions CI, TypeScript strict mode, Ruff/Mypy/Pytest backend gates, eval harness |

## AI/ML Architecture

- **Provider abstraction:** parsing, optimization, truth guard, and embeddings use swappable client/factory layers.
- **Structured LLM path:** OpenAI-compatible chat completions support strict Pydantic schemas, JSON-repair retry, usage metadata, and provider/model observability.
- **Embeddings:** default model is `sentence-transformers/all-MiniLM-L6-v2` with 384-dimensional vectors stored in `resume_embeddings` and `job_embeddings`.
- **Clone-and-run fallback:** if optional local ML dependencies are missing, deterministic fallback embeddings keep analysis/eval flows runnable and record fallback metadata.
- **Hybrid matching:** semantic cosine similarity augments lexical keyword/alias overlap; evidence rows use `semantic` or `hybrid` match types with similarity scores and embedding metadata.
- **Evaluation:** the CLI runner reports parser, matching, semantic, and truth-guard metrics and writes markdown reports under `artifacts/eval_reports/`.

```mermaid
flowchart LR
    Input["Resume + job input"] --> Ingest["Ingestion"]
    Ingest --> Parse["Schema-first parser\nlocal or OpenAI-compatible"]
    Parse --> Embed["Embedding indexing\nMiniLM or deterministic fallback"]
    Embed --> Retrieve["Semantic retrieval\ncosine similarity"]
    Parse --> Lexical["Lexical aliases\nkeyword overlap"]
    Retrieve --> Match["Hybrid match engine"]
    Lexical --> Match
    Match --> Evidence["Persisted evidence rows"]
    Evidence --> Optimize["Resume optimizer"]
    Optimize --> Guard["Truth guard"]
    Guard --> Eval["Eval harness + CI"]
```

Latest local eval snapshot (`--task all --dataset v2 --no-persist`, deterministic embedding fallback because `sentence_transformers` was unavailable):

| Area | Metric | Value |
| --- | --- | --- |
| Resume parser | JSON/schema pass rate | 100.0% / 100.0% |
| Resume parser | Skill F1 | 100.0% |
| Job parser | JSON/schema pass rate | 100.0% / 100.0% |
| Job parser | Skill F1 | 45.5% |
| Matching | Matched skill F1 | 36.2% |
| Matching | Semantic match F1 | 50.0% |
| Matching | Score band accuracy | 54.5% |
| Truth guard | Risky recall / safe precision | 100.0% / 100.0% |
| Truth guard | Unsupported recall / status accuracy | 66.7% / 41.7% |

Phase 5 packaging adds a model/system card, provider matrix, and CI workflow:

- [Model card](docs/model_card.md)
- [Provider matrix](docs/provider_matrix.md)
- [Evaluation plan](docs/evaluation_plan.md)

## Local Development

### Prerequisites

- Node.js 20+
- Python 3.11+
- Docker Desktop, if running the full backend/PostgreSQL stack

### Environment

Copy the environment template:

```bash
cp .env.example .env
```

Important defaults:

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
DATABASE_URL=postgresql+asyncpg://jobfit:jobfit@localhost:5432/jobfit
BACKEND_CORS_ORIGINS=http://localhost:3000
```

### Free Deployment

For a free public deployment, use Render for the FastAPI backend/PostgreSQL and Vercel for the Next.js frontend:

- [Free deployment guide](docs/deployment_free.md)

### Full stack with Docker Compose

```bash
docker compose up --build
```

Services:

- Frontend: <http://localhost:3000>
- Backend API: <http://localhost:8000>
- API docs: <http://localhost:8000/docs>
- PostgreSQL: `localhost:5432`

### Frontend only

```bash
cd frontend
npm install
npm run dev
```

If Next.js shows a stale cache/runtime error after major changes, run:

```bash
npm run dev:clean
```

Validation commands:

```bash
cd frontend
npm run typecheck
npm run build
# or
npm run verify
```

### Backend only

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
# Optional: install local sentence-transformer runtime for real embeddings.
pip install -e ".[dev,local-ml]"
alembic upgrade head
uvicorn app.main:app --reload
```

## API Surface

- `POST /api/analyze` — one-shot resume + JD ingestion, parsing, matching, and optimization
- `GET /api/match-reports/{id}` — read report + evidence rows
- `POST /api/optimizations` — idempotently create/read optimization for a report
- `GET /api/resumes/{id}` — read resume source + parsed JSON
- `GET /api/jobs/{id}` — read job source + parsed JSON
- `GET /health` — backend health check

## Portfolio / CV Positioning

Suggested project line:

> Built JobFit AI, an AI-powered resume-to-job matching system with schema-first OpenAI-compatible LLM pipelines, JSON-repair self-correction, pgvector-backed semantic matching, truth-guarded resume optimization, and CI-backed evaluation reporting.

Impact bullets:

- Designed an end-to-end CV/JD analysis pipeline from document ingestion to shareable report UX.
- Implemented schema-first LLM extraction/optimization with JSON-repair self-correction and local fallbacks.
- Implemented explainable hybrid semantic/lexical scoring with persisted requirement-level evidence rows.
- Added pgvector-backed embedding tables, local sentence-transformer indexing, and deterministic fallback embeddings for clone-and-run demos.
- Built truth-guarded resume rewrite suggestions with local and LLM-entailment guard paths to reduce unsupported or hallucinated claims.
- Added an eval harness with parser/matching/semantic/truth-guard metrics, model/provider docs, and GitHub Actions CI quality gates.

More detail:

- [Case study](docs/case_study.md)
- [CV summary](docs/cv_summary.md)
- [Model card](docs/model_card.md)
- [Provider matrix](docs/provider_matrix.md)
- [PRD](docs/prd.md)
- [Technical architecture](docs/technical_architecture.md)
- [Evaluation plan](docs/evaluation_plan.md)
