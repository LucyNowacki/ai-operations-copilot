from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from .models import ActionItem, ProjectBrief, ProjectNote, ReviewDecision, RiskItem
from .review import apply_decision


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    initialise(conn)
    return conn


def initialise(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS notes (
            note_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            raw_text TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS briefs (
            brief_id TEXT PRIMARY KEY,
            note_id TEXT NOT NULL REFERENCES notes(note_id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            objective TEXT NOT NULL,
            domain TEXT NOT NULL,
            technical_requirements_json TEXT NOT NULL,
            business_value TEXT NOT NULL,
            dependencies_json TEXT NOT NULL,
            owner TEXT NOT NULL,
            priority TEXT NOT NULL,
            due_date TEXT,
            confidence REAL NOT NULL,
            review_state TEXT NOT NULL,
            review_reasons_json TEXT NOT NULL,
            source_references_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS risks (
            risk_id INTEGER PRIMARY KEY AUTOINCREMENT,
            brief_id TEXT NOT NULL REFERENCES briefs(brief_id) ON DELETE CASCADE,
            description TEXT NOT NULL,
            severity TEXT NOT NULL,
            mitigation TEXT NOT NULL,
            requires_review INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS actions (
            action_id INTEGER PRIMARY KEY AUTOINCREMENT,
            brief_id TEXT NOT NULL REFERENCES briefs(brief_id) ON DELETE CASCADE,
            action TEXT NOT NULL,
            owner TEXT NOT NULL,
            due_date TEXT,
            status TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS questions (
            question_id INTEGER PRIMARY KEY AUTOINCREMENT,
            brief_id TEXT NOT NULL REFERENCES briefs(brief_id) ON DELETE CASCADE,
            question TEXT NOT NULL,
            resolved INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS review_decisions (
            decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
            brief_id TEXT NOT NULL REFERENCES briefs(brief_id) ON DELETE CASCADE,
            status TEXT NOT NULL,
            reviewer_notes TEXT NOT NULL,
            reviewer TEXT NOT NULL,
            decided_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            brief_id TEXT,
            event_type TEXT NOT NULL,
            event_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def reset_database(db_path: Path) -> None:
    if db_path.exists():
        db_path.unlink()


def next_id(conn: sqlite3.Connection, table: str, column: str, prefix: str) -> str:
    row = conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
    return f"{prefix}-{int(row['count']) + 1:04d}"


def save_note(conn: sqlite3.Connection, note: ProjectNote) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO notes (note_id, title, source_type, source_path, created_at, raw_text)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            note.note_id,
            note.title,
            note.source_type,
            note.source_path,
            note.created_at.isoformat(),
            note.raw_text,
        ),
    )
    conn.commit()


def save_brief(conn: sqlite3.Connection, brief: ProjectBrief) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO briefs (
            brief_id, note_id, title, objective, domain, technical_requirements_json,
            business_value, dependencies_json, owner, priority, due_date, confidence,
            review_state, review_reasons_json, source_references_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            brief.brief_id,
            brief.note_id,
            brief.title,
            brief.objective,
            brief.domain,
            json.dumps(brief.technical_requirements),
            brief.business_value,
            json.dumps(brief.dependencies),
            brief.owner,
            brief.priority,
            brief.due_date.isoformat() if brief.due_date else None,
            brief.confidence,
            brief.review_state,
            json.dumps(brief.review_reasons),
            json.dumps(brief.source_references),
            brief.created_at.isoformat(),
        ),
    )
    conn.execute("DELETE FROM risks WHERE brief_id = ?", (brief.brief_id,))
    conn.execute("DELETE FROM actions WHERE brief_id = ?", (brief.brief_id,))
    conn.execute("DELETE FROM questions WHERE brief_id = ?", (brief.brief_id,))
    conn.executemany(
        """
        INSERT INTO risks (brief_id, description, severity, mitigation, requires_review)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (brief.brief_id, risk.description, risk.severity, risk.mitigation, int(risk.requires_review))
            for risk in brief.risks
        ],
    )
    conn.executemany(
        """
        INSERT INTO actions (brief_id, action, owner, due_date, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                brief.brief_id,
                action.action,
                action.owner,
                action.due_date.isoformat() if action.due_date else None,
                action.status,
            )
            for action in brief.next_actions
        ],
    )
    conn.executemany(
        "INSERT INTO questions (brief_id, question, resolved) VALUES (?, ?, 0)",
        [(brief.brief_id, question) for question in brief.stakeholder_questions],
    )
    record_audit(conn, brief.brief_id, "brief_saved", {"review_state": brief.review_state})
    conn.commit()


def save_many(conn: sqlite3.Connection, notes_and_briefs: Iterable[tuple[ProjectNote, ProjectBrief]]) -> None:
    for note, brief in notes_and_briefs:
        save_note(conn, note)
        save_brief(conn, brief)


def fetch_brief(conn: sqlite3.Connection, brief_id: str) -> ProjectBrief:
    row = conn.execute("SELECT * FROM briefs WHERE brief_id = ?", (brief_id,)).fetchone()
    if row is None:
        raise KeyError(f"Unknown brief_id: {brief_id}")
    risks = [
        RiskItem(
            description=risk["description"],
            severity=risk["severity"],
            mitigation=risk["mitigation"],
            requires_review=bool(risk["requires_review"]),
        )
        for risk in conn.execute("SELECT * FROM risks WHERE brief_id = ? ORDER BY risk_id", (brief_id,))
    ]
    actions = [
        ActionItem(
            action=action["action"],
            owner=action["owner"],
            due_date=action["due_date"],
            status=action["status"],
        )
        for action in conn.execute("SELECT * FROM actions WHERE brief_id = ? ORDER BY action_id", (brief_id,))
    ]
    questions = [
        question["question"]
        for question in conn.execute(
            "SELECT * FROM questions WHERE brief_id = ? AND resolved = 0 ORDER BY question_id",
            (brief_id,),
        )
    ]
    return ProjectBrief(
        brief_id=row["brief_id"],
        note_id=row["note_id"],
        title=row["title"],
        objective=row["objective"],
        domain=row["domain"],
        technical_requirements=json.loads(row["technical_requirements_json"]),
        business_value=row["business_value"],
        risks=risks,
        dependencies=json.loads(row["dependencies_json"]),
        owner=row["owner"],
        priority=row["priority"],
        due_date=row["due_date"],
        stakeholder_questions=questions,
        next_actions=actions,
        confidence=row["confidence"],
        review_state=row["review_state"],
        review_reasons=json.loads(row["review_reasons_json"]),
        source_references=json.loads(row["source_references_json"]),
        created_at=row["created_at"],
    )


def fetch_briefs(conn: sqlite3.Connection) -> list[ProjectBrief]:
    rows = conn.execute("SELECT brief_id FROM briefs ORDER BY created_at, brief_id").fetchall()
    return [fetch_brief(conn, row["brief_id"]) for row in rows]


def store_review_decision(conn: sqlite3.Connection, decision: ReviewDecision) -> ProjectBrief:
    brief = fetch_brief(conn, decision.brief_id)
    updated = apply_decision(brief, decision)
    conn.execute(
        """
        INSERT INTO review_decisions (brief_id, status, reviewer_notes, reviewer, decided_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            decision.brief_id,
            decision.status,
            decision.reviewer_notes,
            decision.reviewer,
            decision.decided_at.isoformat(),
        ),
    )
    save_brief(conn, updated)
    record_audit(
        conn,
        decision.brief_id,
        "review_decision",
        {"status": decision.status, "reviewer": decision.reviewer},
    )
    conn.commit()
    return updated


def record_audit(conn: sqlite3.Connection, brief_id: str | None, event_type: str, event: dict[str, object]) -> None:
    conn.execute(
        "INSERT INTO audit_events (brief_id, event_type, event_json, created_at) VALUES (?, ?, ?, ?)",
        (brief_id, event_type, json.dumps(event, sort_keys=True), datetime.now(UTC).isoformat()),
    )


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    tables = ["notes", "briefs", "risks", "actions", "questions", "review_decisions", "audit_events"]
    return {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}
