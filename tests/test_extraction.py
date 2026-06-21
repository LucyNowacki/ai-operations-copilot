from pathlib import Path

import pytest

from ai_ops_copilot.extractor import ExtractionError, RuleBasedExtractor, parse_llm_json, validate_brief_payload
from ai_ops_copilot.models import ProjectNote
from ai_ops_copilot.review import can_finalise


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "data" / "examples"


def test_valid_portfolio_note_creates_complete_project_brief() -> None:
    path = EXAMPLES / "semantic_recommender_product.md"
    note = ProjectNote(note_id="NOTE-0001", title="Semantic Recommender Product Brief", raw_text=path.read_text())

    brief = RuleBasedExtractor().extract(note, "BRIEF-0001")

    assert brief.domain == "recommender_systems"
    assert brief.objective
    assert brief.technical_requirements
    assert brief.business_value
    assert brief.next_actions
    assert brief.confidence > 0


def test_at_least_three_portfolio_examples_extract_successfully() -> None:
    paths = [
        EXAMPLES / "medical_wound_launch.md",
        EXAMPLES / "fintech_options_risk.md",
        EXAMPLES / "climate_dmd_brief.md",
    ]

    briefs = [
        RuleBasedExtractor().extract(
            ProjectNote(note_id=f"NOTE-{index:04d}", title=path.stem, raw_text=path.read_text()),
            f"BRIEF-{index:04d}",
        )
        for index, path in enumerate(paths, start=1)
    ]

    assert {brief.domain for brief in briefs} == {"medical_ai", "fintech_analytics", "climate_modelling"}


def test_missing_owner_or_due_date_is_handled_and_flagged() -> None:
    note = ProjectNote(
        note_id="NOTE-X",
        title="Ambiguous AI project",
        raw_text="Build an AI dashboard from notes. We need a useful project plan but the owner and deadline are not known.",
    )

    brief = RuleBasedExtractor().extract(note, "BRIEF-X")

    assert brief.owner == "unassigned"
    assert brief.due_date is None
    assert brief.review_state == "pending_review"
    assert "unclear owner" in brief.review_reasons


def test_malformed_llm_json_is_rejected() -> None:
    with pytest.raises(ExtractionError):
        parse_llm_json("{not-valid-json")


def test_schema_validation_rejects_missing_fields_invalid_priority_and_bad_due_date() -> None:
    payload = {
        "brief_id": "BRIEF-BAD",
        "note_id": "NOTE-BAD",
        "title": "Bad brief",
        "objective": "Bad output",
        "domain": "medical_ai",
        "technical_requirements": ["schema"],
        "business_value": "None",
        "risks": [],
        "owner": "Lucy",
        "priority": "immediate",
        "due_date": "not-a-date",
        "next_actions": [],
        "confidence": 0.9,
    }

    with pytest.raises(ExtractionError):
        validate_brief_payload(payload)


def test_high_risk_output_cannot_finalise_without_human_approval() -> None:
    path = EXAMPLES / "robotics_drone_agent_workflow.md"
    note = ProjectNote(note_id="NOTE-DRONE", title="Robotics Drone Agent Workflow", raw_text=path.read_text())

    brief = RuleBasedExtractor().extract(note, "BRIEF-DRONE")

    assert brief.domain == "robotics_agents"
    assert brief.review_state == "pending_review"
    assert not can_finalise(brief)
