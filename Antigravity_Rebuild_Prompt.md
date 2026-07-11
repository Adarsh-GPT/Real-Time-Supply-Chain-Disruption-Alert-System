# Master Prompt — Rebuild "Real-Time Supply Chain Disruption Alert System" as a Production-Grade Project

> Paste this whole document into Antigravity IDE as your working brief. It's written as a single agent prompt with phased tasks, so you can also paste it phase-by-phase if you want tighter review checkpoints.

---

## 0. Role & Framing (paste this first)

```
You are a Staff AI/ML Engineer with 20+ years of experience spanning frontend,
backend, data engineering, ML, and applied AI systems. You have been handed an
existing repo — a student-level prototype called "Real-Time Supply Chain
Disruption Alert System" — and asked to rebuild it into a production-grade,
portfolio/interview-ready system. Treat this as if you were doing a real
paid contract: correct architecture, real data pipelines, tests, CI/CD,
observability, security, and documentation. Do not just polish the surface —
re-architect anything that doesn't hold up under a system-design interview
question. Work in small, reviewable commits. After each phase, give me a
summary of what changed and why, and flag any decisions you made on my behalf
so I can override them.

Current repo: https://github.com/Adarsh-GPT/Real-Time-Supply-Chain-Disruption-Alert-System
Current stack: Python, pandas/numpy, NLTK + VADER sentiment, TF-IDF +
Logistic Regression (weak-supervised on VADER labels), Streamlit dashboard,
Firebase auth, NewsAPI + Guardian API ingestion, Kaggle historical dataset.
Current weaknesses to fix: no real "real-time" pipeline (it's polling, not
streaming/event-driven), no persistent database, no automated tests, no CI/CD,
no containerization, no monitoring/logging, weak labels only (no gold-labeled
eval set), single monolithic Streamlit script, no API layer separating
model/backend from UI, no retry/error handling on external API calls, secrets
likely hardcoded, no scalability story, README is descriptive but has no
architecture diagram, no deployed demo link.

Your mandate: rebuild this into something that would survive a technical
interview walkthrough — "walk me through your architecture", "how do you
handle a source going down", "how would this scale to 1M headlines/day",
"how do you retrain safely", "how do you know your model isn't drifting".
```

---

## 1. Target Architecture (what "done" looks like)

Give the agent this explicit target so it doesn't just refactor in place:

```
Rebuild the system with this architecture:

INGESTION LAYER
- Scheduled + event-driven ingestion workers (Python) pulling from NewsAPI,
  GNews, and The Guardian API, with a pluggable "Source" interface so adding
  a new feed is a 20-line class, not a rewrite.
- Use APScheduler or a lightweight Celery + Redis queue for polling on
  intervals (e.g., every 5 min), OR simulate real "streaming" with Kafka
  (or Redpanda, or even a local Redis Streams substitute if Kafka is too
  heavy for a portfolio project) so the ingestion → processing → alerting
  path is genuinely event-driven, not a Streamlit script re-running on
  refresh.
- Deduplicate headlines (hash + fuzzy match) before they hit the pipeline.
- Store raw ingested data in a "bronze" table/collection before any
  processing (so nothing is lost and reprocessing is possible).

PROCESSING / NLP LAYER
- Clean text processing module (tokenization, stemming/lemmatization) kept,
  but decoupled into its own package with unit tests.
- Keep VADER as a fast baseline signal, but add:
  - A proper supervised model: TF-IDF + Logistic Regression AND a second
    model (e.g., DistilBERT or a small transformer via HuggingFace, or
    at minimum an XGBoost/LightGBM model on richer features) so you can
    demo a model comparison / ensembling story.
  - A held-out, hand-labeled evaluation set (even 200-300 manually labeled
    headlines) so accuracy numbers are defensible, not just self-generated
    from VADER labels grading VADER-derived labels.
  - Model versioning via MLflow (or a simple model registry pattern:
    versioned artifacts in S3/GCS or local /models/v{n}/ with a
    metadata.json recording metrics, training date, data hash).
  - A confidence score + explainability layer (e.g., top TF-IDF terms
    driving the classification, or SHAP values) surfaced in the UI —
    this is a strong interview talking point.
- Entity extraction (spaCy NER) to tag headlines with country/company/port
  entities, enabling "risk by region" and "risk by company" views.

RISK SCORING / BUSINESS LOGIC LAYER
- A rules + ML hybrid risk engine: combine sentiment score, ML classifier
  output, entity risk weighting (e.g., a headline mentioning a major port
  weighted higher), and recency decay into a single explainable risk score.
- Configurable thresholds (YAML/config file, not hardcoded) for Low/Medium/
  High so a non-engineer could tune it.

STORAGE
- Replace ad hoc CSV/session-state storage with a real database:
  PostgreSQL for structured headline + risk records, with a proper schema
  (sources, headlines, risk_scores, alerts, users).
  Optionally add a vector store (pgvector, Chroma, or FAISS) for semantic
  search over headlines ("show me things similar to this disruption").
- Add a simple data model diagram (ERD).

API LAYER
- Build a FastAPI backend exposing REST endpoints: /headlines, /risk-scores,
  /alerts, /search, /auth. This decouples business logic from the UI so the
  frontend could be Streamlit today and React tomorrow.
- Add request validation (Pydantic), pagination, rate limiting, and OpenAPI
  docs (FastAPI gives you this for free — make sure it's actually clean).

ALERTING LAYER
- Real alert delivery: when risk crosses a threshold, push a notification
  via email (SendGrid/SMTP) and/or Slack webhook and/or Telegram bot —
  pick at least one and implement it fully, don't just print to console.
- Alert de-duplication/throttling so the same disruption doesn't spam.

FRONTEND / DASHBOARD
- Keep Streamlit (fast to build, fine for portfolio) but rebuild the UI to
  call the FastAPI backend instead of doing everything inline. Add:
  - Real-time-feeling auto-refresh (st.autorefresh or websockets)
  - Risk map (folium/pydeck) showing geographic risk if entities extracted
  - Trend charts over time (Plotly) by category/region
  - Drill-down from a risk alert to the source headlines
  - Proper auth (Firebase is fine, but wire it through the API layer with
    JWT session tokens, not just client-side Streamlit checks)

MLOPS / ENGINEERING HYGIENE
- requirements.txt split into requirements/base.txt, dev.txt, prod.txt (or
  use poetry/uv with a lockfile).
- Dockerfile + docker-compose.yml (services: api, worker, postgres, redis,
  streamlit) so `docker compose up` gives a full working stack.
- pytest test suite: unit tests for text cleaning, risk scoring logic, API
  endpoints (using FastAPI's TestClient), and at least one integration test
  for the ingestion → risk score pipeline using mocked API responses.
- GitHub Actions CI: lint (ruff/flake8), type-check (mypy), test on push,
  and a build step that builds the Docker image.
- Structured logging (structlog or Python logging with JSON formatter) and
  a basic health-check endpoint (/health) so this looks operable, not just
  runnable.
- Config via .env + pydantic-settings, with a .env.example committed and
  real secrets never committed (add a pre-commit hook or gitleaks check).
- A Makefile or justfile with make setup / make test / make run / make
  docker-up so a reviewer can get this running in 3 commands.

DEPLOYMENT
- Deploy a live demo: Streamlit Community Cloud or Render/Railway for the
  API + a managed Postgres (Supabase/Neon free tier) + Streamlit Cloud for
  the UI. Put the live link at the top of the README.

DOCUMENTATION (this matters as much as the code for a portfolio project)
- Rewrite README with: problem statement, architecture diagram (draw it —
  Mermaid diagram in the README is fine), tech stack table, setup
  instructions, screenshots/GIF of the dashboard, model performance table,
  "design decisions & tradeoffs" section (this is what interviewers actually
  read), and a "what I'd do with more time" section.
- Add a one-page ARCHITECTURE.md going deeper for engineers who want detail.
- Add docstrings + type hints across all modules.
```

---

## 2. Phased Execution Plan (give the agent this so it doesn't try to do everything in one giant unreviewable diff)

```
Execute in these phases. After each phase, stop, summarize the diff, and
wait for my go-ahead before continuing:

Phase 1 — Audit & Plan
- Clone/inspect the current repo structure fully.
- Produce a written gap analysis against the target architecture above.
- Propose the new repo folder structure (e.g., /ingestion, /processing,
  /risk_engine, /api, /dashboard, /models, /tests, /infra, /docs).
- Propose the DB schema (ERD in Mermaid).
Do not write implementation code yet in this phase.

Phase 2 — Core Refactor (no new infra yet)
- Break the monolith into packages per the folder structure.
- Add Pydantic config, structured logging, .env handling.
- Add pytest scaffolding + first unit tests for existing text-cleaning and
  sentiment/risk logic so we have a safety net before bigger changes.

Phase 3 — Data & Storage
- Stand up Postgres via docker-compose, write the schema/migrations
  (Alembic), and migrate storage from ad hoc files to the DB.

Phase 4 — API Layer
- Build the FastAPI service wrapping the risk engine and DB, with
  OpenAPI docs, auth middleware, and tests.

Phase 5 — ML Upgrade
- Add the second model, the hand-labeled eval set, model versioning, and
  explainability layer. Produce a model comparison report (markdown table
  + a couple of charts) as an artifact.

Phase 6 — Ingestion & Alerting
- Move ingestion to the scheduler/queue pattern, add dedup, add the real
  alert delivery channel(s).

Phase 7 — Frontend Rebuild
- Rebuild the Streamlit dashboard against the new API, add the map/trend
  views and drill-downs.

Phase 8 — DevOps
- Dockerize everything, write docker-compose, add GitHub Actions CI, add
  Makefile.

Phase 9 — Deploy & Document
- Deploy the live demo, rewrite README + ARCHITECTURE.md, add screenshots,
  record a short demo GIF.

Phase 10 — Interview Prep Pass
- Generate a document of likely interview questions about this project
  (system design, ML, and behavioral "walk me through a decision") with
  strong sample answers based on what was actually built, including
  honest tradeoffs and what you'd improve with more time/budget.
```

---

## 3. Guardrails to give the agent

```
- Don't fabricate metrics, screenshots, or claims in the README — every
  number must come from an actual run/test in this repo.
- Keep API keys and secrets out of git at all times; use .env + secret
  scanning.
- Prefer free/low-cost tiers for any hosted service (Neon/Supabase free
  Postgres, Render/Railway free web service, Streamlit Community Cloud)
  since this is a portfolio project, not funded infra.
- Optimize for "explainable in a 10-minute interview walkthrough" over
  maximal complexity — every added component should have a clear reason
  you can state out loud.
- Commit in small, logical chunks with clear messages; don't squash the
  whole rebuild into one commit.
```

---

## How to use this

1. Open the repo in Antigravity IDE.
2. Paste **Section 0** first so the agent has the right framing and knows the repo/stack.
3. Paste **Section 1** as the target spec.
4. Paste **Section 2** to force phased, reviewable execution — approve each phase before moving on.
5. Paste **Section 3** as standing guardrails.
6. After Phase 10, you'll have: a live demo link, a real architecture, tests + CI, and a prepared interview narrative — exactly what turns "a nephew's college project" into a genuine hiring-manager-impressing portfolio piece.
