from pathlib import Path

from dashboard.app import project_url_for
from dashboard.data import brief_rows, open_risks, priority_distribution, review_queue, unresolved_questions
from ai_ops_copilot.pipeline import run_demo


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "data" / "examples"


def test_dashboard_data_functions_return_summary_tables(tmp_path: Path) -> None:
    outputs = run_demo(EXAMPLES, tmp_path)

    briefs = brief_rows(outputs.database)
    priorities = priority_distribution(outputs.database)
    risks = open_risks(outputs.database)
    questions = unresolved_questions(outputs.database)
    reviews = review_queue(outputs.database)

    assert len(briefs) == 6
    assert not priorities.empty
    assert not risks.empty
    assert not questions.empty
    assert not reviews.empty


def test_project_links_prefer_portfolio_pages_then_github() -> None:
    assert project_url_for({"domain": "climate_modelling"}).startswith("https://lucynowacki.github.io/blog/dmd")
    assert "lucynowacki.github.io/blog/method-of-lines" in project_url_for({"domain": "fintech_analytics"})
    assert project_url_for({"domain": "medical_ai"}) == "https://github.com/LucyNowacki/CancerDetector"
    assert project_url_for({"domain": "recommender_systems"}) == "https://github.com/LucyNowacki/Semantic-Recommender"
    assert project_url_for({"domain": "robotics_agents"}) == "https://lucynowacki.github.io"
