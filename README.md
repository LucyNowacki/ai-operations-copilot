# AI Operations Copilot / Career Proof Engine

AI Operations Copilot is a portfolio-aware workflow engine that turns messy project notes into structured, reviewable launch briefs, risks, owner actions, stakeholder questions and dashboard summaries. It demonstrates how modern AI tools can be used as part of an integrated, auditable workflow rather than as isolated assistants.

## Business Problem

AI, data and operations teams often start from unclear notes: meeting transcripts, CRM comments, support tickets, GitHub summaries or portfolio project descriptions. Useful work gets delayed because objectives, owners, deadlines, risks and stakeholder questions are scattered. This project shows how an AI-assisted workflow can structure that information, validate it, store it, visualise it and require human review before high-risk outputs are finalised.

## Why It Matters In 2026

Employers increasingly need people who can make AI behave like reliable software: structured outputs, validation, review gates, audit trails, workflow automation and clear stakeholder communication. This project demonstrates those skills with examples grounded in Lucy Nowacki's public portfolio and GitHub: medical AI, wound diagnostics, recommender systems, fintech modelling, climate DMD, PINNs, NLP deployment, adversarial robustness, robotics and AI-agent workflows.

## What It Demonstrates

- Python project structure with a CLI and Streamlit dashboard.
- Pydantic-style schemas for project notes, briefs, risks, actions and review decisions.
- Offline LLM-style structured extraction plus an optional OpenAI-compatible adapter.
- SQLite storage with documented SQL queries.
- Human-in-the-loop review for high-risk, ambiguous or low-confidence outputs.
- n8n-style webhook automation design.
- Linux/API examples using Bash, environment variables, `curl`, `jq` and JSON.
- Responsible-AI governance: review gates, audit trail, PII awareness and source checking.
- Pytest coverage for validation, malformed output, database persistence, review refusal and dashboard data.

## Portfolio-Grounded Demo Domains

The example inputs in `data/examples/` are based on Lucy's public profile:

- medical AI / wound diagnostics;
- fintech analytics / option pricing / risk;
- climate modelling / Dynamic Mode Decomposition;
- scientific ML / PINNs / numerical PDEs;
- recommender systems / semantic search;
- NLP / hate-speech detection / Azure deployment;
- robotics / drones / AI-agent workflows.

## Architecture

```text
Markdown project notes
        |
        v
RuleBasedExtractor or optional OpenAI-compatible extractor
        |
        +-- Pydantic validation
        +-- confidence and review-gate rules
        +-- responsible-AI risk checks
        |
        v
SQLite database
        |
        +-- Streamlit dashboard
        +-- SQL reports
        +-- n8n-style webhook payloads
        +-- human review decisions and audit events
```

## Setup

```bash
cd ai-operations-copilot
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

The default `.env.example` uses `AI_PROVIDER=offline`, so the demo runs without API keys or internet access. Do not commit real secrets.

## Run The Demo

```bash
python -m ai_ops_copilot.cli run-demo
python -m ai_ops_copilot.cli export-summary
streamlit run dashboard/app.py
```

Generated outputs:

- `outputs/career_proof.db`
- `outputs/career_proof_summary.json`
- `outputs/webhook_payloads.jsonl`

Example CLI review command:

```bash
python -m ai_ops_copilot.cli review \
  --brief-id BRIEF-0001 \
  --status approved \
  --notes "Reviewed for portfolio demo; keep medical output advisory."
```

## Tests

```bash
pytest
```

The tests cover:

- valid portfolio notes creating complete project briefs;
- at least three portfolio/GitHub examples extracting successfully;
- missing owner or due date handled without crashing;
- ambiguous input flagged for human review;
- malformed LLM JSON rejected;
- high-risk medical/defence/financial outputs blocked until human approval;
- SQLite write/read preserving briefs, risks, actions and review states;
- dashboard data functions for priority distribution, open risks and questions.

## Responsible AI And Governance

The system deliberately treats AI output as a proposal, not truth.

- **Human approval:** high-risk, low-confidence, clinical, defence, drone, financial, regulatory or unclear-owner outputs enter review.
- **Prompt/version tracking:** live LLM usage should record prompt version, model name and schema version before production use.
- **Audit trail:** database tables store notes, briefs, review decisions and audit events.
- **PII awareness:** medical and support notes should be redacted before live LLM calls.
- **Hallucination risk:** extracted claims should remain linked to source notes and reviewer questions.
- **Source checking:** scientific, financial and clinical outputs should cite data sources and assumptions before sign-off.
- **When not to automate:** do not automate clinical decisions, investment advice, defence actions or safety-critical robotics actions without qualified human approval.

Example refusal: the drone/defence demo and wound-diagnostics demo are marked `pending_review`; they cannot be treated as final until a reviewer approves them.

## Automation Layer

The `/automation/` folder contains:

- n8n workflow concept and Mermaid diagram;
- webhook payload example;
- n8n-style JSON concept workflow;
- Linux/API examples with Bash, `curl`, `jq`, JSON and environment variables.

n8n, Codex, Cursor, Claude Code and GitHub Copilot are workflow aids, not runtime dependencies. The project explains how these tools can assist planning, implementation, review, documentation and automation without pretending they are all required to run the app.

## Limitations

- The default extractor is deterministic so tests and demos are reproducible; it is not a replacement for a production LLM.
- The live LLM adapter is intentionally minimal and must be configured with local secrets.
- The Streamlit dashboard is a prototype interface, not a multi-user application.
- Example notes are portfolio-grounded synthetic inputs, not private client data.

## Future Improvements

- Add LangGraph-style stateful orchestration for multi-step review flows.
- Add prompt and schema version tracking.
- Add OpenTelemetry or Langfuse-style tracing.
- Add richer source citation and PII redaction.
- Add a small REST API if backend integration becomes more important than the Streamlit dashboard.

## CV-ready Bullets

### AI Operations / Gravitee-Style Role

- Built a portfolio-aware AI Operations Copilot in Python that converts messy project notes into structured launch briefs using schema-validated LLM-style extraction, SQLite audit storage and human-in-the-loop review.
- Designed n8n-style webhook automation and review callbacks for AI-agent workflows, showing how model outputs can be governed before they trigger downstream actions.

### Data Analyst / Analytics Role

- Developed a Streamlit dashboard and SQL-backed reporting layer for project briefs, open risks, owners, priorities, unresolved stakeholder questions and review status.
- Added pytest coverage for parsing, schema validation, malformed model output, database write/read and dashboard summary functions.

### Fintech / Growth Analytics Role

- Created fintech and risk-analysis demo briefs grounded in Black-Scholes, Method of Lines, time-series analytics and stakeholder-ready reporting.
- Implemented review gates for financial-risk and investment-advice language, demonstrating responsible analytics workflow design.

### AI Engineer / Startup Role

- Implemented an offline-first AI extraction architecture with an optional OpenAI-compatible provider, Pydantic validation, review-state handling and auditable SQLite persistence.
- Grounded demo data in public GitHub/portfolio projects across medical AI, semantic search, NLP deployment, climate modelling, scientific ML and robotics-agent workflows.
