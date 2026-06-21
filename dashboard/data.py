from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


def load_table(db_path: Path, table: str) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame()
    conn = sqlite3.connect(db_path)
    try:
        return pd.read_sql_query(f"SELECT * FROM {table}", conn)
    finally:
        conn.close()


def brief_rows(db_path: Path) -> pd.DataFrame:
    return load_table(db_path, "briefs")


def open_risks(db_path: Path) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame()
    conn = sqlite3.connect(db_path)
    try:
        return pd.read_sql_query(
            """
            SELECT b.brief_id, b.title, b.domain, b.priority, r.severity, r.description, r.mitigation
            FROM risks r
            JOIN briefs b ON b.brief_id = r.brief_id
            WHERE r.requires_review = 1 OR r.severity IN ('high', 'critical')
            ORDER BY b.brief_id
            """,
            conn,
        )
    finally:
        conn.close()


def unresolved_questions(db_path: Path) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame()
    conn = sqlite3.connect(db_path)
    try:
        return pd.read_sql_query(
            """
            SELECT b.brief_id, b.title, q.question
            FROM questions q
            JOIN briefs b ON b.brief_id = q.brief_id
            WHERE q.resolved = 0
            ORDER BY b.brief_id, q.question_id
            """,
            conn,
        )
    finally:
        conn.close()


def review_queue(db_path: Path) -> pd.DataFrame:
    briefs = brief_rows(db_path)
    if briefs.empty:
        return pd.DataFrame()
    return briefs[briefs["review_state"].isin(["pending_review", "needs_info", "rejected"])].copy()


def priority_distribution(db_path: Path) -> pd.DataFrame:
    briefs = brief_rows(db_path)
    if briefs.empty:
        return pd.DataFrame(columns=["priority", "project_count"])
    return (
        briefs.groupby("priority", as_index=False)
        .size()
        .rename(columns={"size": "project_count"})
        .sort_values("priority")
    )


def status_summary(db_path: Path) -> pd.DataFrame:
    briefs = brief_rows(db_path)
    if briefs.empty:
        return pd.DataFrame(columns=["review_state", "project_count"])
    return briefs.groupby("review_state", as_index=False).size().rename(columns={"size": "project_count"})
