from pathlib import Path

from ai_ops_copilot.models import ReviewDecision
from ai_ops_copilot.pipeline import ingest_folder
from ai_ops_copilot.review import can_finalise
from ai_ops_copilot.storage import connect, fetch_brief, fetch_briefs, store_review_decision, table_counts


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "data" / "examples"


def test_database_write_read_preserves_briefs_risks_actions_and_review_state(tmp_path: Path) -> None:
    db_path = tmp_path / "career_proof.db"
    ingest_folder(db_path, EXAMPLES)

    conn = connect(db_path)
    try:
        counts = table_counts(conn)
        briefs = fetch_briefs(conn)
    finally:
        conn.close()

    assert counts["notes"] == 6
    assert counts["briefs"] == 6
    assert counts["risks"] >= 6
    assert counts["actions"] >= 6
    assert counts["questions"] >= 1
    assert any(brief.review_state == "pending_review" for brief in briefs)


def test_human_approval_allows_high_risk_brief_to_finalise(tmp_path: Path) -> None:
    db_path = tmp_path / "career_proof.db"
    ingest_folder(db_path, EXAMPLES)

    conn = connect(db_path)
    try:
        brief = fetch_brief(conn, "BRIEF-0001")
        assert not can_finalise(brief)

        updated = store_review_decision(
            conn,
            ReviewDecision(
                brief_id="BRIEF-0001",
                status="approved",
                reviewer_notes="Approved for portfolio demo with advisory wording.",
            ),
        )
    finally:
        conn.close()

    assert updated.review_state == "approved"
    assert can_finalise(updated)
