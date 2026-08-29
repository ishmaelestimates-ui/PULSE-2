"""
Pydantic schemas for the executive dashboard.
"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.dashboard import MilestoneStatus


class MilestoneCreate(BaseModel):
    title: str
    due_date: Optional[date] = None
    notes: Optional[str] = None


class MilestoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    episode_id: int
    title: str
    due_date: Optional[date]
    completed_date: Optional[date]
    status: MilestoneStatus
    notes: Optional[str]
    created_at: datetime
    overdue: bool = False


class TimelineResponse(BaseModel):
    episode_id: int
    milestones: list[MilestoneOut]


class BudgetItemCreate(BaseModel):
    category: str
    amount: float
    spent: float = 0.0
    notes: Optional[str] = None


class BudgetItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    episode_id: int
    category: str
    amount: float
    spent: float
    notes: Optional[str]


class FinancesResponse(BaseModel):
    episode_id: int
    items: list[BudgetItemOut]
    total_budget: float
    total_spent: float
    remaining: float
    reallocation_suggestions: list[str]
    note: str = "User-entered budget data — PULSE doesn't connect to any accounting system."


class RiskItem(BaseModel):
    category: str  # Legal | Schedule | Financial | Creative
    severity: str  # high | medium | low
    description: str
    recommended_action: str


class RisksResponse(BaseModel):
    episode_id: int
    risks: list[RiskItem]
    note: str = (
        "Rule-based, computed from PULSE's own tracked data (unverified "
        "festival deadlines, overdue milestones, budget overruns, "
        "unreviewed weak sections, unresolved sync-licensing flags) — not "
        "an external audit."
    )


class DashboardResponse(BaseModel):
    episode_id: int
    progress: dict[str, float]  # stage -> 0-100
    overall_progress: float
    health_score: float  # 0-100, deterministic formula — see dashboard_service
    critical_path: list[str]
    upcoming_deadlines: list[dict]
    team_status_note: str = (
        "PULSE has no multi-user/team accounts yet, so there's no real "
        "team-member data to show here."
    )
    note: str = (
        "health_score and progress are computed from PULSE's own tracked "
        "completion state (uploads, reviews, generated assets) using a "
        "simple weighted formula — not an external or industry benchmark."
    )
