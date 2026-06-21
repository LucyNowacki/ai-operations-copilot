from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .extractor import Extractor, extractor_from_env
from .models import ProjectBrief, ProjectNote
from .review import can_finalise
from .storage import connect, fetch_briefs, next_id, reset_database, save_brief, save_note, table_counts
from .webhook import to_webhook_payload, write_jsonl


@dataclass(frozen=True)
class PipelineOutputs:
    database: Path
    summary_json: Path
    webhook_payloads: Path
    brief_count: int


def note_from_file(path: Path, note_id: str) -> ProjectNote:
    raw_text = path.read_text(encoding="utf-8")
    title = extract_title(raw_text, path)
    return ProjectNote(
        note_id=note_id,
        title=title,
        source_type="portfolio_summary",
        source_path=str(path),
        raw_text=raw_text,
    )


def extract_title(raw_text: str, path: Path) -> str:
    for line in raw_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return path.stem.replace("_", " ").replace("-", " ").title()


def ingest_example(db_path: Path, example_path: Path, extractor: Extractor | None = None) -> ProjectBrief:
    extractor = extractor or extractor_from_env()
    conn = connect(db_path)
    try:
        note_id = next_id(conn, "notes", "note_id", "NOTE")
        brief_id = next_id(conn, "briefs", "brief_id", "BRIEF")
        note = note_from_file(example_path, note_id)
        brief = extractor.extract(note, brief_id)
        save_note(conn, note)
        save_brief(conn, brief)
        return brief
    finally:
        conn.close()


def ingest_folder(db_path: Path, examples_dir: Path, extractor: Extractor | None = None) -> list[ProjectBrief]:
    extractor = extractor or extractor_from_env()
    conn = connect(db_path)
    briefs: list[ProjectBrief] = []
    try:
        for path in sorted(examples_dir.glob("*.md")):
            note_id = next_id(conn, "notes", "note_id", "NOTE")
            brief_id = next_id(conn, "briefs", "brief_id", "BRIEF")
            note = note_from_file(path, note_id)
            brief = extractor.extract(note, brief_id)
            save_note(conn, note)
            save_brief(conn, brief)
            briefs.append(brief)
        return briefs
    finally:
        conn.close()


def run_demo(examples_dir: Path, out_dir: Path, db_name: str = "career_proof.db") -> PipelineOutputs:
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / db_name
    reset_database(db_path)
    briefs = ingest_folder(db_path, examples_dir)
    summary_path = out_dir / "career_proof_summary.json"
    webhook_path = out_dir / "webhook_payloads.jsonl"
    export_summary(db_path, summary_path)
    write_jsonl(webhook_path, (to_webhook_payload(brief) for brief in briefs))
    return PipelineOutputs(
        database=db_path,
        summary_json=summary_path,
        webhook_payloads=webhook_path,
        brief_count=len(briefs),
    )


def export_summary(db_path: Path, out_path: Path | None = None) -> dict[str, object]:
    conn = connect(db_path)
    try:
        briefs = fetch_briefs(conn)
        summary = {
            "brief_count": len(briefs),
            "finalisable_count": sum(1 for brief in briefs if can_finalise(brief)),
            "review_queue_count": sum(1 for brief in briefs if brief.review_state in {"pending_review", "needs_info"}),
            "priority_distribution": distribution([brief.priority for brief in briefs]),
            "domain_distribution": distribution([brief.domain for brief in briefs]),
            "open_risks": [
                {
                    "brief_id": brief.brief_id,
                    "title": brief.title,
                    "severity": risk.severity,
                    "description": risk.description,
                    "mitigation": risk.mitigation,
                }
                for brief in briefs
                for risk in brief.risks
            ],
            "unresolved_questions": [
                {"brief_id": brief.brief_id, "title": brief.title, "question": question}
                for brief in briefs
                for question in brief.stakeholder_questions
            ],
            "table_counts": table_counts(conn),
        }
    finally:
        conn.close()

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def distribution(values: list[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        result[value] = result.get(value, 0) + 1
    return dict(sorted(result.items()))
