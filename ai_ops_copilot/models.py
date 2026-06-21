from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Domain = Literal[
    "medical_ai",
    "fintech_analytics",
    "climate_modelling",
    "scientific_ml",
    "recommender_systems",
    "nlp_deployment",
    "robotics_agents",
    "general_ai_operations",
]

Priority = Literal["low", "medium", "high", "critical"]
ReviewState = Literal["draft", "pending_review", "approved", "rejected", "needs_info"]
ReviewStatus = Literal["approved", "rejected", "needs_info"]
ActionStatus = Literal["open", "in_progress", "done", "blocked"]
SourceType = Literal[
    "meeting_notes",
    "crm_note",
    "project_description",
    "support_ticket",
    "portfolio_summary",
    "github_summary",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class ProjectNote(StrictModel):
    note_id: str
    title: str
    source_type: SourceType = "project_description"
    source_path: str = ""
    created_at: date = Field(default_factory=date.today)
    raw_text: str

    @field_validator("title", "raw_text")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field must not be blank")
        return value


class RiskItem(StrictModel):
    description: str
    severity: Priority
    mitigation: str
    requires_review: bool = False

    @field_validator("description", "mitigation")
    @classmethod
    def risk_text_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("risk description and mitigation are required")
        return value


class ActionItem(StrictModel):
    action: str
    owner: str = "unassigned"
    due_date: date | None = None
    status: ActionStatus = "open"

    @field_validator("action")
    @classmethod
    def action_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("action must not be blank")
        return value

    @field_validator("owner")
    @classmethod
    def owner_default(cls, value: str) -> str:
        value = value.strip()
        return value or "unassigned"


class ProjectBrief(StrictModel):
    brief_id: str
    note_id: str
    title: str
    objective: str
    domain: Domain
    technical_requirements: list[str]
    business_value: str
    risks: list[RiskItem]
    dependencies: list[str] = Field(default_factory=list)
    owner: str = "unassigned"
    priority: Priority
    due_date: date | None = None
    stakeholder_questions: list[str] = Field(default_factory=list)
    next_actions: list[ActionItem]
    confidence: float = Field(ge=0, le=1)
    review_state: ReviewState = "draft"
    review_reasons: list[str] = Field(default_factory=list)
    source_references: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("title", "objective", "business_value")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("required text field must not be blank")
        return value

    @field_validator("technical_requirements", "next_actions")
    @classmethod
    def required_lists(cls, value: list[Any]) -> list[Any]:
        if not value:
            raise ValueError("technical requirements and next actions must not be empty")
        return value

    @field_validator("owner")
    @classmethod
    def default_owner(cls, value: str) -> str:
        value = value.strip()
        return value or "unassigned"

    @property
    def requires_human_review(self) -> bool:
        return self.review_state in {"pending_review", "needs_info"} or bool(self.review_reasons)


class ReviewDecision(StrictModel):
    brief_id: str
    status: ReviewStatus
    reviewer_notes: str
    reviewer: str = "human_reviewer"
    decided_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("brief_id", "reviewer_notes")
    @classmethod
    def decision_text_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("review decision fields must not be blank")
        return value
