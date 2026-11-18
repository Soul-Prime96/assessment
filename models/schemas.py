"""
Pydantic schemas for structured agent outputs.
All agents return validated instances of these models, ensuring
reliable data contracts between the orchestrator and subagents.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ExceptionSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionPriority(int, Enum):
    LOWEST = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    CRITICAL = 5


class WorkflowStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


# ---------------------------------------------------------------------------
# Data Analyst Output
# ---------------------------------------------------------------------------

class TrendDirection(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    STABLE = "STABLE"


class KPIMetric(BaseModel):
    name: str = Field(description="KPI display name, e.g. 'Total Revenue'")
    value: float = Field(description="Current computed value")
    unit: str = Field(default="", description="Unit label, e.g. '$', '%', 'units'")
    period: str = Field(default="", description="Time period, e.g. 'Last 30 days'")
    previous_value: Optional[float] = Field(default=None, description="Prior period value for delta")
    change_pct: Optional[float] = Field(default=None, description="% change vs previous period")
    trend: TrendDirection = Field(default=TrendDirection.STABLE)


class AnomalyFlag(BaseModel):
    metric: str
    value: float
    expected_range: tuple[float, float]
    z_score: float
    description: str


class DataSummary(BaseModel):
    source_file: str
    records_processed: int
    date_range: str
    kpis: list[KPIMetric] = Field(default_factory=list)
    anomalies: list[AnomalyFlag] = Field(default_factory=list)
    top_performers: list[str] = Field(default_factory=list, description="Top product/region/channel names")
    underperformers: list[str] = Field(default_factory=list)
    summary_text: str = Field(default="", description="Natural language summary of key findings")


# ---------------------------------------------------------------------------
# Workflow Manager Output
# ---------------------------------------------------------------------------

class WorkflowTask(BaseModel):
    task_name: str
    status: WorkflowStatus
    output_path: Optional[str] = None
    message: str = ""
    executed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class WorkflowResult(BaseModel):
    tasks_executed: int
    tasks_succeeded: int
    tasks_failed: int
    tasks: list[WorkflowTask] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list, description="Paths of generated output files")


# ---------------------------------------------------------------------------
# Exception Monitor Output
# ---------------------------------------------------------------------------

class ExceptionReport(BaseModel):
    exception_id: str = Field(description="Unique ID, e.g. EXC-001")
    rule_name: str = Field(description="Name of the violated business rule")
    severity: ExceptionSeverity
    description: str
    affected_dimension: str = Field(description="e.g. 'Product: Widget A', 'Region: North'")
    actual_value: float
    threshold_value: float
    unit: str = ""
    detected_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Recommender Output
# ---------------------------------------------------------------------------

class ActionRecommendation(BaseModel):
    recommendation_id: str = Field(description="e.g. REC-001")
    action: str = Field(description="Short imperative action title")
    rationale: str = Field(description="Why this action is recommended")
    linked_exceptions: list[str] = Field(
        default_factory=list,
        description="Exception IDs that triggered this recommendation",
    )
    priority: ActionPriority
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0–1")
    estimated_impact: str = Field(default="", description="Expected business impact if actioned")
    requires_human_approval: bool = Field(
        default=False,
        description="True for HIGH/CRITICAL priority or irreversible actions",
    )
    suggested_owner: str = Field(default="", description="Role or team, e.g. 'Sales Manager'")
    deadline: Optional[str] = Field(default=None, description="ISO date if time-sensitive")


# ---------------------------------------------------------------------------
# Orchestrator Aggregate Output
# ---------------------------------------------------------------------------

class HumanDecision(BaseModel):
    recommendation_id: str
    approved: bool
    reviewer: str = "human_operator"
    notes: str = ""
    decided_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class OrchestratorSummary(BaseModel):
    session_id: str
    run_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data_summary: Optional[DataSummary] = None
    exceptions: list[ExceptionReport] = Field(default_factory=list)
    recommendations: list[ActionRecommendation] = Field(default_factory=list)
    workflow_result: Optional[WorkflowResult] = None
    human_decisions: list[HumanDecision] = Field(default_factory=list)
    critical_count: int = 0
    high_count: int = 0
    auto_actioned_count: int = 0
    pending_human_review_count: int = 0
    executive_summary: str = ""
