from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .models import ReviewDecision
from .pipeline import export_summary, ingest_example, ingest_folder, run_demo
from .review import can_finalise
from .storage import connect, fetch_brief, fetch_briefs, store_review_decision


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = PROJECT_ROOT / "outputs" / "career_proof.db"
DEFAULT_EXAMPLES = PROJECT_ROOT / "data" / "examples"


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Operations Copilot / Career Proof Engine")
    parser.add_argument("--db", type=Path, default=Path(os.getenv("DATABASE_PATH", DEFAULT_DB)))
    sub = parser.add_subparsers(dest="command", required=True)

    one = sub.add_parser("ingest-example", help="Ingest one Markdown project note")
    one.add_argument("path", type=Path)

    folder = sub.add_parser("ingest-folder", help="Ingest all Markdown examples in a folder")
    folder.add_argument("path", type=Path, nargs="?", default=DEFAULT_EXAMPLES)

    review = sub.add_parser("review", help="Apply a human review decision")
    review.add_argument("--brief-id", required=True)
    review.add_argument("--status", choices=["approved", "rejected", "needs_info"], required=True)
    review.add_argument("--notes", required=True)
    review.add_argument("--reviewer", default="human_reviewer")

    sub.add_parser("export-summary", help="Print JSON project/status summary")
    sub.add_parser("run-demo", help="Reset demo DB, ingest portfolio examples and export artifacts")

    args = parser.parse_args()
    if args.command == "ingest-example":
        brief = ingest_example(args.db, args.path)
        _print_brief_result(brief.brief_id, args.db)
    elif args.command == "ingest-folder":
        briefs = ingest_folder(args.db, args.path)
        print(json.dumps({"database": str(args.db), "brief_count": len(briefs)}, indent=2))
    elif args.command == "review":
        decision = ReviewDecision(
            brief_id=args.brief_id,
            status=args.status,
            reviewer_notes=args.notes,
            reviewer=args.reviewer,
        )
        conn = connect(args.db)
        try:
            updated = store_review_decision(conn, decision)
        finally:
            conn.close()
        print(
            json.dumps(
                {
                    "brief_id": updated.brief_id,
                    "review_state": updated.review_state,
                    "can_finalise": can_finalise(updated),
                },
                indent=2,
            )
        )
    elif args.command == "export-summary":
        print(json.dumps(export_summary(args.db), indent=2, sort_keys=True))
    elif args.command == "run-demo":
        outputs = run_demo(DEFAULT_EXAMPLES, PROJECT_ROOT / "outputs")
        print(
            json.dumps(
                {
                    "database": str(outputs.database),
                    "summary_json": str(outputs.summary_json),
                    "webhook_payloads": str(outputs.webhook_payloads),
                    "brief_count": outputs.brief_count,
                },
                indent=2,
            )
        )


def _print_brief_result(brief_id: str, db_path: Path) -> None:
    conn = connect(db_path)
    try:
        brief = fetch_brief(conn, brief_id)
    finally:
        conn.close()
    print(
        json.dumps(
            {
                "database": str(db_path),
                "brief_id": brief.brief_id,
                "title": brief.title,
                "domain": brief.domain,
                "priority": brief.priority,
                "review_state": brief.review_state,
                "can_finalise": can_finalise(brief),
            },
            indent=2,
        )
    )


def list_briefs(db_path: Path) -> list[dict[str, object]]:
    conn = connect(db_path)
    try:
        return [
            {
                "brief_id": brief.brief_id,
                "title": brief.title,
                "domain": brief.domain,
                "priority": brief.priority,
                "review_state": brief.review_state,
            }
            for brief in fetch_briefs(conn)
        ]
    finally:
        conn.close()


if __name__ == "__main__":
    main()
