from __future__ import annotations

from collections import Counter
from statistics import mean

from .models import ProjectBrief


def build_quality_report(briefs: list[ProjectBrief]) -> dict[str, object]:
    """Summarise extraction quality, review pressure and portfolio coverage."""

    return {
        "brief_count": len(briefs),
        "domain_distribution": dict(sorted(Counter(brief.domain for brief in briefs).items())),
        "priority_distribution": dict(sorted(Counter(brief.priority for brief in briefs).items())),
        "review_state_distribution": dict(sorted(Counter(brief.review_state for brief in briefs).items())),
        "average_confidence": round(mean([brief.confidence for brief in briefs]), 3) if briefs else 0,
        "review_required_count": sum(1 for brief in briefs if brief.requires_human_review),
        "open_risk_count": sum(len(brief.risks) for brief in briefs),
        "open_question_count": sum(len(brief.stakeholder_questions) for brief in briefs),
    }
