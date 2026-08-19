from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.aggregate_analysis import AggregateAnalysisResponse
from app.schemas.analysis import (
    AppliedSchemaMapping,
    DataQualitySummary,
    FunnelAnalysis,
    GrowthMetrics,
)
from app.schemas.analysis_context import AnalysisContext


ConfidenceLevel = Literal["high", "medium", "low"]


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AIReportRequest(StrictSchema):
    dataset_type: Literal["user_level", "aggregate_metrics"] = "user_level"
    analysis_context: AnalysisContext | None = None
    schema_mapping: AppliedSchemaMapping | None = None
    data_quality: DataQualitySummary | None = None
    metrics: GrowthMetrics | None = None
    funnel: FunnelAnalysis | None = None
    channels: dict[str, GrowthMetrics] | None = None
    aggregate_analysis: AggregateAnalysisResponse | None = None

    @model_validator(mode="after")
    def validate_dataset_payload(self) -> Self:
        if self.dataset_type == "aggregate_metrics":
            if self.aggregate_analysis is None:
                raise ValueError("aggregate_metrics 缺少 aggregate_analysis。")
            if self.aggregate_analysis.dataset_type != "aggregate_metrics":
                raise ValueError("aggregate_analysis 数据类型不匹配。")
            return self

        required_fields = {
            "analysis_context": self.analysis_context,
            "schema_mapping": self.schema_mapping,
            "data_quality": self.data_quality,
            "metrics": self.metrics,
            "funnel": self.funnel,
            "channels": self.channels,
        }
        missing = [
            field_name
            for field_name, value in required_fields.items()
            if value is None
        ]
        if missing:
            raise ValueError(
                "user_level 缺少字段：" + "、".join(missing)
            )
        return self


class DraftReportEvidence(StrictSchema):
    evidence_ref: list[str] = Field(min_length=1, max_length=4)
    interpretation: str = Field(min_length=1)


class DraftKeyIssue(StrictSchema):
    issue: str = Field(min_length=1)
    evidence: list[DraftReportEvidence] = Field(min_length=1, max_length=3)
    impact: str = Field(min_length=1)
    confidence: ConfidenceLevel


class DraftPriorityAction(StrictSchema):
    action: str = Field(min_length=1)
    applicable_to: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    experiment: str | None = None
    target_metric: str = Field(min_length=1)


class DraftGrowthOpportunity(StrictSchema):
    target: str = Field(min_length=1)
    evidence: list[DraftReportEvidence] = Field(min_length=1, max_length=2)
    recommendation: str = Field(min_length=1)


class DraftGrowthExplanation(BaseModel):
    # Legacy/model-supplied authority fields are intentionally ignored. The
    # backend binds the dimension and injects its deterministic driver.
    model_config = ConfigDict(extra="ignore")

    why: str = Field(min_length=1)
    main_contribution: str = Field(min_length=1)
    evidence: list[DraftReportEvidence] = Field(min_length=1, max_length=3)


class AIReportDraft(StrictSchema):
    core_conclusion: str = Field(min_length=1, max_length=240)
    growth_explanation: DraftGrowthExplanation | None = None
    key_issues: list[DraftKeyIssue] = Field(default_factory=list, max_length=3)
    priority_actions: list[DraftPriorityAction] = Field(
        default_factory=list,
        max_length=3,
    )
    opportunities: list[DraftGrowthOpportunity] = Field(
        default_factory=list,
        max_length=2,
    )
    limitations: list[str] = Field(default_factory=list, max_length=5)


class ReportEvidence(StrictSchema):
    evidence_ref: list[str] = Field(min_length=1, max_length=4)
    display_values: list[str] = Field(min_length=1, max_length=4)
    interpretation: str = Field(min_length=1)


class KeyIssue(StrictSchema):
    issue: str = Field(min_length=1)
    evidence: list[ReportEvidence] = Field(min_length=1, max_length=3)
    impact: str = Field(min_length=1)
    confidence: ConfidenceLevel


class PriorityAction(StrictSchema):
    action: str = Field(min_length=1)
    applicable_to: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    experiment: str | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    target_metric: str = Field(min_length=1)


class GrowthOpportunity(StrictSchema):
    target: str = Field(min_length=1)
    evidence: list[ReportEvidence] = Field(min_length=1, max_length=2)
    recommendation: str = Field(min_length=1)


class GrowthExplanation(StrictSchema):
    dimension_value: str = Field(min_length=1)
    growth_driver: Literal[
        "traffic",
        "conversion",
        "combined",
        "mixed",
        "unavailable",
    ]
    why: str = Field(min_length=1)
    main_contribution: str = Field(min_length=1)
    evidence: list[ReportEvidence] = Field(min_length=1, max_length=3)


class AIReportResponse(StrictSchema):
    core_conclusion: str = Field(min_length=1, max_length=240)
    growth_explanation: GrowthExplanation | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    key_issues: list[KeyIssue] = Field(default_factory=list, max_length=3)
    priority_actions: list[PriorityAction] = Field(
        default_factory=list,
        max_length=3,
    )
    opportunities: list[GrowthOpportunity] = Field(
        default_factory=list,
        max_length=2,
    )
    limitations: list[str] = Field(default_factory=list, max_length=5)
