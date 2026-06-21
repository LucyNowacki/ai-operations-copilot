from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import date
from typing import Any, Protocol

from pydantic import ValidationError

from .models import ActionItem, Domain, Priority, ProjectBrief, ProjectNote, RiskItem
from .review import review_reasons_for


class ExtractionError(ValueError):
    """Raised when an LLM-style response cannot be parsed or validated."""


class Extractor(Protocol):
    def extract(self, note: ProjectNote, brief_id: str) -> ProjectBrief:
        """Return a validated project brief."""


class RuleBasedExtractor:
    """Deterministic extractor used for offline demos and tests.

    It mirrors structured-output LLM behaviour: produce a JSON-like payload,
    validate it through the same model contract, then apply review gates.
    """

    def extract(self, note: ProjectNote, brief_id: str) -> ProjectBrief:
        text = f"{note.title}\n{note.raw_text}"
        domain = detect_domain(text)
        priority = detect_priority(text, domain)
        owner = extract_owner(text)
        due_date = extract_due_date(text)
        confidence = confidence_for(text, owner, due_date, domain)
        risks = build_risks(text, domain, priority)
        actions = build_actions(text, domain, owner, due_date)
        questions = build_questions(text, owner, due_date, risks)
        requirements = build_requirements(text, domain)

        payload = {
            "brief_id": brief_id,
            "note_id": note.note_id,
            "title": note.title,
            "objective": build_objective(note, domain),
            "domain": domain,
            "technical_requirements": requirements,
            "business_value": build_business_value(domain),
            "risks": [risk.model_dump(mode="json") for risk in risks],
            "dependencies": build_dependencies(domain),
            "owner": owner,
            "priority": priority,
            "due_date": due_date.isoformat() if due_date else None,
            "stakeholder_questions": questions,
            "next_actions": [action.model_dump(mode="json") for action in actions],
            "confidence": confidence,
            "review_state": "draft",
            "review_reasons": [],
            "source_references": [note.source_path or note.source_type],
        }
        brief = validate_brief_payload(payload)
        reasons = review_reasons_for(note.raw_text, brief)
        return brief.model_copy(
            update={
                "review_state": "pending_review" if reasons else "draft",
                "review_reasons": reasons,
            }
        )


class OpenAICompatibleExtractor:
    """Optional live extractor for OpenAI-compatible chat-completions APIs."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("AI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("AI_MODEL") or "gpt-4.1-mini"
        if not self.api_key:
            raise ExtractionError("OPENAI_API_KEY is required for openai_compatible provider")

    def extract(self, note: ProjectNote, brief_id: str) -> ProjectBrief:
        prompt = build_extraction_prompt(note, brief_id)
        request_body = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Return only valid JSON matching the requested project brief schema.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(request_body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ExtractionError(f"Live LLM extraction failed: {exc}") from exc

        content = body["choices"][0]["message"]["content"]
        brief = parse_llm_json(content)
        reasons = review_reasons_for(note.raw_text, brief)
        return brief.model_copy(
            update={
                "review_state": "pending_review" if reasons else brief.review_state,
                "review_reasons": sorted(set(brief.review_reasons + reasons)),
            }
        )


def extractor_from_env() -> Extractor:
    provider = os.getenv("AI_PROVIDER", "offline").strip().lower()
    if provider == "openai_compatible":
        return OpenAICompatibleExtractor()
    return RuleBasedExtractor()


def parse_llm_json(raw: str) -> ProjectBrief:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"Malformed LLM JSON: {exc}") from exc
    return validate_brief_payload(payload)


def validate_brief_payload(payload: dict[str, Any]) -> ProjectBrief:
    try:
        return ProjectBrief.model_validate(payload)
    except ValidationError as exc:
        raise ExtractionError(f"Project brief failed schema validation: {exc}") from exc


def build_extraction_prompt(note: ProjectNote, brief_id: str) -> str:
    return json.dumps(
        {
            "task": "Extract a structured project brief from messy notes.",
            "brief_id": brief_id,
            "note": note.model_dump(mode="json"),
            "required_fields": [
                "objective",
                "domain",
                "technical_requirements",
                "business_value",
                "risks",
                "dependencies",
                "owner",
                "priority",
                "due_date",
                "stakeholder_questions",
                "next_actions",
                "confidence",
                "review_state",
            ],
        },
        indent=2,
    )


def detect_domain(text: str) -> Domain:
    lowered = text.lower()
    domain_terms: list[tuple[Domain, tuple[str, ...]]] = [
        ("medical_ai", ("wound", "medical", "clinical", "patient", "histopathological", "diagnosis")),
        ("climate_modelling", ("climate", "el nino", "el niño", "dmd", "dynamic mode")),
        ("fintech_analytics", ("black-scholes", "option", "fintech", "financial risk", "market", "crypto")),
        ("scientific_ml", ("pinn", "physics-informed", "neural operator", "pde", "method of lines")),
        ("recommender_systems", ("recommender", "semantic search", "embedding", "hdbscan", "umap")),
        ("nlp_deployment", ("hate speech", "xlstm", "azure", "nlp", "moderation")),
        ("robotics_agents", ("drone", "uav", "robot", "prosthetic", "agent workflow", "defence")),
    ]
    for domain, terms in domain_terms:
        if any(term in lowered for term in terms):
            return domain
    return "general_ai_operations"


def detect_priority(text: str, domain: Domain) -> Priority:
    lowered = text.lower()
    if any(term in lowered for term in ["critical", "patient safety", "defence", "regulatory", "investment advice"]):
        return "critical"
    if any(term in lowered for term in ["urgent", "high risk", "launch", "deadline", "go-live"]):
        return "high"
    if domain in {"medical_ai", "fintech_analytics", "robotics_agents"}:
        return "high"
    return "medium"


def extract_owner(text: str) -> str:
    patterns = [
        r"\bowner\s*:\s*([^\n.;]+)",
        r"\blead\s*:\s*([^\n.;]+)",
        r"\bresponsible\s*:\s*([^\n.;]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return "unassigned"


def extract_due_date(text: str) -> date | None:
    match = re.search(r"\b(?:due|deadline|target date)\s*:\s*(\d{4}-\d{2}-\d{2})\b", text, flags=re.IGNORECASE)
    if not match:
        match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if not match:
        return None
    return date.fromisoformat(match.group(1))


def confidence_for(text: str, owner: str, due_date: date | None, domain: Domain) -> float:
    score = 0.58
    if owner != "unassigned":
        score += 0.12
    if due_date:
        score += 0.08
    if domain != "general_ai_operations":
        score += 0.12
    if len(text.split()) > 80:
        score += 0.06
    return round(min(score, 0.95), 3)


def build_objective(note: ProjectNote, domain: Domain) -> str:
    first_sentence = re.split(r"(?<=[.!?])\s+", meaningful_text(note.raw_text))[0]
    if len(first_sentence) > 180:
        first_sentence = first_sentence[:177].rstrip() + "..."
    return f"Turn {note.title} into a structured {domain.replace('_', ' ')} launch brief: {first_sentence}"


def meaningful_text(raw_text: str) -> str:
    skipped_prefixes = (
        "source:",
        "owner:",
        "due:",
        "deadline:",
        "target date:",
    )
    lines = []
    for line in raw_text.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        if not stripped or stripped.startswith("#") or lowered.startswith(skipped_prefixes):
            continue
        lines.append(stripped)
    return " ".join(lines) or raw_text.strip()


def build_business_value(domain: Domain) -> str:
    values = {
        "medical_ai": "Improves clinical triage planning while keeping safety-sensitive decisions under review.",
        "fintech_analytics": "Connects mathematical modelling to risk-aware product, analytics and stakeholder decisions.",
        "climate_modelling": "Turns scientific modelling outputs into explainable climate-risk actions and questions.",
        "scientific_ml": "Frames numerical PDE and scientific ML work as a reproducible product workflow.",
        "recommender_systems": "Converts semantic search capability into a measurable product-discovery workflow.",
        "nlp_deployment": "Links NLP model development to deployment, moderation quality and Azure-ready operations.",
        "robotics_agents": "Structures robotics and agent workflows around safety, owners, dependencies and approvals.",
        "general_ai_operations": "Turns unstructured AI project notes into stakeholder-ready operating plans.",
    }
    return values[domain]


def build_requirements(text: str, domain: Domain) -> list[str]:
    base = ["Structured extraction schema", "Human review workflow", "SQLite audit trail"]
    domain_requirements = {
        "medical_ai": ["Image model evaluation", "PII-aware data handling", "Clinical safety review"],
        "fintech_analytics": ["Python analytics pipeline", "Risk metric validation", "SQL reporting"],
        "climate_modelling": ["DMD feature extraction", "Time-series diagnostics", "Model interpretability notes"],
        "scientific_ml": ["PINN/PDE experiment tracking", "Numerical validation", "Reproducible training notes"],
        "recommender_systems": ["Embedding pipeline", "Semantic retrieval evaluation", "Recommendation quality metrics"],
        "nlp_deployment": ["Text classification checks", "Azure deployment handoff", "Robustness evaluation"],
        "robotics_agents": ["Agent workflow definition", "Safety gate", "Hardware/software dependency tracking"],
        "general_ai_operations": ["Project brief extraction", "Risk and action tracking", "Stakeholder summary"],
    }
    requirements = base + domain_requirements[domain]
    if "dashboard" in text.lower():
        requirements.append("Stakeholder dashboard")
    return requirements


def build_dependencies(domain: Domain) -> list[str]:
    common = ["portfolio source notes", "human reviewer", "project owner confirmation"]
    domain_dependencies = {
        "medical_ai": ["image data governance", "clinical review policy"],
        "fintech_analytics": ["market data source", "risk methodology sign-off"],
        "climate_modelling": ["time-series dataset", "scientific validation notes"],
        "scientific_ml": ["PDE definition", "experiment configuration"],
        "recommender_systems": ["embedding model", "evaluation dataset"],
        "nlp_deployment": ["labelled text sample", "deployment environment"],
        "robotics_agents": ["simulation environment", "safety checklist"],
        "general_ai_operations": ["business context", "review rubric"],
    }
    return common + domain_dependencies[domain]


def build_risks(text: str, domain: Domain, priority: Priority) -> list[RiskItem]:
    risk = {
        "medical_ai": ("Clinical or patient-safety output could be over-trusted.", "Keep outputs advisory and require expert approval."),
        "fintech_analytics": ("Financial risk output could be mistaken for investment advice.", "Label analytics as decision support and require review."),
        "climate_modelling": ("DMD patterns could be over-interpreted without source checking.", "Keep source references and validation notes with every brief."),
        "scientific_ml": ("PINN or PDE outputs may hide numerical instability.", "Track assumptions, residuals and validation tests."),
        "recommender_systems": ("Semantic search may surface plausible but weakly relevant recommendations.", "Evaluate retrieval quality and expose confidence."),
        "nlp_deployment": ("NLP moderation may contain bias or robustness failures.", "Use adversarial tests and human review for sensitive content."),
        "robotics_agents": ("Autonomous workflow could create safety or defence misuse risk.", "Require explicit human approval before operational use."),
        "general_ai_operations": ("Ambiguous notes may produce incomplete actions.", "Ask stakeholder questions before finalising."),
    }[domain]
    requires_review = priority in {"high", "critical"} or domain in {"medical_ai", "fintech_analytics", "robotics_agents"}
    return [RiskItem(description=risk[0], severity=priority, mitigation=risk[1], requires_review=requires_review)]


def build_actions(text: str, domain: Domain, owner: str, due_date: date | None) -> list[ActionItem]:
    actions = {
        "medical_ai": "Prepare wound-diagnostics launch brief and clinical review checklist.",
        "fintech_analytics": "Define risk metrics, data inputs and stakeholder dashboard requirements.",
        "climate_modelling": "Summarise DMD modelling assumptions and validation questions.",
        "scientific_ml": "Document PINN/PDE experiment design, validation metrics and next tests.",
        "recommender_systems": "Prepare semantic-search product brief with evaluation metrics.",
        "nlp_deployment": "Create NLP deployment brief covering Azure handoff and robustness checks.",
        "robotics_agents": "Map agent workflow, safety gates and hardware/software dependencies.",
        "general_ai_operations": "Clarify owner, objective, deadline and review criteria.",
    }
    return [ActionItem(action=actions[domain], owner=owner, due_date=due_date)]


def build_questions(text: str, owner: str, due_date: date | None, risks: list[RiskItem]) -> list[str]:
    questions: list[str] = []
    if owner == "unassigned":
        questions.append("Who is the accountable owner for this project?")
    if due_date is None:
        questions.append("What is the target due date or review date?")
    if any(risk.requires_review for risk in risks):
        questions.append("Who must approve the high-risk output before it is finalised?")
    if "data" not in text.lower():
        questions.append("Which source data or evidence should be checked before implementation?")
    return questions or ["What evidence would make this brief ready for stakeholder sign-off?"]
