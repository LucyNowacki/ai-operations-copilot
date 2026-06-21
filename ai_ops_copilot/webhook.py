from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import ProjectBrief


def to_webhook_payload(brief: ProjectBrief) -> dict[str, object]:
    """Return an n8n-style payload for downstream review automation."""

    return {
        "workflow": "career_proof_project_brief_review",
        "event": "brief.structured_output_created",
        "brief_id": brief.brief_id,
        "note_id": brief.note_id,
        "title": brief.title,
        "domain": brief.domain,
        "priority": brief.priority,
        "owner": brief.owner,
        "due_date": brief.due_date.isoformat() if brief.due_date else None,
        "review_state": brief.review_state,
        "review_reasons": brief.review_reasons,
        "confidence": round(brief.confidence, 3),
        "objective": brief.objective,
        "business_value": brief.business_value,
        "risk_count": len(brief.risks),
        "open_question_count": len(brief.stakeholder_questions),
        "callback_urls": {
            "approve": f"https://ops.example.test/webhooks/review/{brief.brief_id}/approve",
            "needs_info": f"https://ops.example.test/webhooks/review/{brief.brief_id}/needs-info",
            "reject": f"https://ops.example.test/webhooks/review/{brief.brief_id}/reject",
        },
    }


def write_jsonl(path: Path, payloads: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for payload in payloads:
            fh.write(json.dumps(payload, sort_keys=True) + "\n")
