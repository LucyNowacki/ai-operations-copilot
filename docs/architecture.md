# Architecture

```text
Markdown project notes in data/examples/
        |
        v
RuleBasedExtractor or optional OpenAI-compatible extractor
        |
        +-- Pydantic schema validation
        +-- confidence scoring
        +-- responsible-AI review gates
        |
        v
SQLite store
        |
        +-- notes
        +-- briefs
        +-- risks
        +-- actions
        +-- questions
        +-- review_decisions
        +-- audit_events
        |
        +--> Streamlit dashboard
        +--> SQL examples
        +--> n8n-style webhook payloads
```

## Design Choices

- AI output is treated as proposed structure, not truth.
- The offline extractor keeps demos and tests reproducible.
- The optional OpenAI-compatible adapter is isolated behind the same schema contract.
- SQLite gives a simple audit trail for notes, briefs, risks, actions and human decisions.
- Streamlit is the v1 interface because it is fast to run and easy for recruiters to inspect.
- n8n is documented as an integration layer, not a runtime dependency.

## Review Gate

A brief enters `pending_review` when confidence is low, ownership is unclear, priority is high or critical, or the source mentions clinical, defence, drone, financial, regulatory or patient-safety risk. High-risk outputs must not be finalised until a reviewer approves them.

## Portfolio Alignment

The demo examples are grounded in Lucy Nowacki's public work:

- `CancerDetector` and `AzureCancerDetector` -> medical AI and wound-diagnostics workflow.
- `Semantic-Recommender` -> recommender-system product brief.
- `Method-of-Lines-BlackScholes` and finance posts -> fintech risk analytics.
- `DMD` and climate posts -> climate-risk modelling brief.
- `PINNs` and numerical PDE posts -> scientific ML workflow.
- xLSTM hate-speech projects and adversarial attacks -> NLP deployment and robustness.
- UAV, robotics and prosthetics portfolio themes -> AI-agent workflow and safety review.
