from __future__ import annotations

import os
import sys
from html import escape
from pathlib import Path

import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.data import brief_rows, open_risks, priority_distribution, review_queue, status_summary, unresolved_questions

DEFAULT_DB = PROJECT_ROOT / "outputs" / "career_proof.db"

PROJECT_LINKS = {
    "climate_modelling": "https://lucynowacki.github.io/blog/dmd-for-el-nino/",
    "fintech_analytics": "https://lucynowacki.github.io/blog/method-of-lines-for-black-scholes-explicit/",
    "medical_ai": "https://github.com/LucyNowacki/CancerDetector",
    "nlp_deployment": "https://github.com/LucyNowacki/Azure-HateDetector-Deployment",
    "recommender_systems": "https://github.com/LucyNowacki/Semantic-Recommender",
    "robotics_agents": "https://lucynowacki.github.io",
}


def main() -> None:
    st.set_page_config(page_title="AI Operations Copilot", layout="wide")
    st.title("AI Operations Copilot / Career Proof Engine")
    st.caption("Portfolio-grounded project briefs, risks, owners, questions and human-review state.")

    db_path = Path(os.getenv("DATABASE_PATH", DEFAULT_DB))
    st.sidebar.header("Data")
    st.sidebar.code(str(db_path))

    briefs = brief_rows(db_path)
    if briefs.empty:
        st.warning("No project briefs found. Run `python -m ai_ops_copilot.cli run-demo` first.")
        return

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Project briefs", len(briefs))
    col_b.metric("Review queue", len(review_queue(db_path)))
    col_c.metric("Open risks", len(open_risks(db_path)))

    left, right = st.columns([2, 1])
    with left:
        st.subheader("Project Briefs")
        st.markdown(render_project_briefs_table(briefs), unsafe_allow_html=True)
    with right:
        st.subheader("Priority Distribution")
        priorities = priority_distribution(db_path)
        fig = px.bar(priorities, x="priority", y="project_count", text="project_count")
        st.plotly_chart(fig, use_container_width=True)

    selected = st.selectbox("Selected brief", briefs["brief_id"].tolist())
    selected_row = briefs[briefs["brief_id"] == selected].iloc[0]
    st.subheader(selected_row["title"])
    st.write(selected_row["objective"])
    st.markdown(f"**Business value:** {selected_row['business_value']}")
    st.markdown(f"**Review state:** `{selected_row['review_state']}`")

    tab_risks, tab_questions, tab_review, tab_status = st.tabs(
        ["Open risks", "Unresolved questions", "Review queue", "Status summary"]
    )
    with tab_risks:
        st.dataframe(open_risks(db_path), use_container_width=True, hide_index=True)
    with tab_questions:
        st.dataframe(unresolved_questions(db_path), use_container_width=True, hide_index=True)
    with tab_review:
        st.dataframe(
            review_queue(db_path)[["brief_id", "title", "priority", "review_state", "review_reasons_json"]],
            use_container_width=True,
            hide_index=True,
        )
    with tab_status:
        st.dataframe(status_summary(db_path), use_container_width=True, hide_index=True)

def compact_description(row) -> str:
    value = str(row.get("business_value", "")).strip()
    if not value:
        value = str(row.get("objective", "")).strip()
    return value[:150] + ("..." if len(value) > 150 else "")


def project_url_for(row) -> str:
    return PROJECT_LINKS.get(str(row.get("domain", "")), "https://lucynowacki.github.io")


def render_project_briefs_table(briefs) -> str:
    rows = []
    for _, row in briefs.iterrows():
        tooltip = escape(compact_description(row), quote=True)
        url = escape(project_url_for(row), quote=True)
        title = escape(str(row["title"]))
        cells = [
            f'<td title="{tooltip}"><code>{escape(str(row["brief_id"]))}</code></td>',
            f'<td title="{tooltip}"><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></td>',
            f'<td title="{tooltip}">{escape(str(row["domain"]).replace("_", " "))}</td>',
            f'<td title="{tooltip}"><span class="priority priority-{escape(str(row["priority"]))}">{escape(str(row["priority"]))}</span></td>',
            f'<td title="{tooltip}">{escape(str(row["owner"]))}</td>',
            f'<td title="{tooltip}">{escape(str(row["due_date"] or ""))}</td>',
            f'<td title="{tooltip}">{escape(str(row["review_state"]).replace("_", " "))}</td>',
            f'<td title="{tooltip}">{float(row["confidence"]):.2f}</td>',
        ]
        rows.append("<tr>" + "".join(cells) + "</tr>")

    return """
<style>
.brief-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}
.brief-table th,
.brief-table td {
  border-bottom: 1px solid rgba(128, 128, 128, 0.25);
  padding: 0.45rem 0.5rem;
  vertical-align: top;
}
.brief-table th {
  text-align: left;
  font-weight: 700;
}
.brief-table a {
  font-weight: 650;
  text-decoration: none;
}
.brief-table a:hover {
  text-decoration: underline;
}
.priority {
  border-radius: 0.25rem;
  padding: 0.1rem 0.35rem;
  font-size: 0.78rem;
  font-weight: 700;
}
.priority-critical { background: #7f1d1d; color: #fff; }
.priority-high { background: #9a3412; color: #fff; }
.priority-medium { background: #854d0e; color: #fff; }
.priority-low { background: #166534; color: #fff; }
</style>
<table class="brief-table">
  <thead>
    <tr>
      <th>ID</th>
      <th>Project</th>
      <th>Domain</th>
      <th>Priority</th>
      <th>Owner</th>
      <th>Due</th>
      <th>Review</th>
      <th>Conf.</th>
    </tr>
  </thead>
  <tbody>
""" + "\n".join(rows) + """
  </tbody>
</table>
"""


if __name__ == "__main__":
    main()
