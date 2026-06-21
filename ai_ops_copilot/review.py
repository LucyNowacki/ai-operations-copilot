from __future__ import annotations

from .models import ProjectBrief, ProjectNote, ReviewDecision


REVIEW_THRESHOLD = 0.75
HIGH_RISK_TERMS = {
    "clinical decision": "clinical decision risk",
    "clinical": "clinical or medical safety risk",
    "patient safety": "patient-safety risk",
    "defence": "defence or dual-use risk",
    "drone": "robotics/autonomy safety risk",
    "uav": "robotics/autonomy safety risk",
    "financial risk": "financial-risk exposure",
    "investment advice": "investment-advice risk",
    "regulatory": "regulatory exposure",
    "regulator": "regulatory exposure",
}


def review_reasons_for(raw_text: str, brief: ProjectBrief) -> list[str]:
    text = raw_text.lower()
    reasons: list[str] = []
    if brief.confidence < REVIEW_THRESHOLD:
        reasons.append("low extraction confidence")
    if brief.priority in {"high", "critical"}:
        reasons.append(f"{brief.priority} priority")
    if brief.owner == "unassigned":
        reasons.append("unclear owner")
    for term, reason in HIGH_RISK_TERMS.items():
        if term in text and reason not in reasons:
            reasons.append(reason)
    if any(risk.requires_review for risk in brief.risks):
        reasons.append("risk item requires human review")
    return sorted(set(reasons))


def can_finalise(brief: ProjectBrief) -> bool:
    if not brief.requires_human_review:
        return True
    return brief.review_state == "approved"


def apply_decision(brief: ProjectBrief, decision: ReviewDecision) -> ProjectBrief:
    if decision.status == "approved":
        return brief.model_copy(update={"review_state": "approved", "review_reasons": []})
    if decision.status == "rejected":
        return brief.model_copy(update={"review_state": "rejected"})
    return brief.model_copy(update={"review_state": "needs_info"})
