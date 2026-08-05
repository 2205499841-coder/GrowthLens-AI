from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.analysis import (
    AppliedSchemaMapping,
    DataQualitySummary,
    FunnelAnalysis,
    GrowthMetrics,
)
from app.schemas.analysis_context import AnalysisContext


ExpectedDirection = Literal["increase", "decrease", "maintain"]


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AIReportRequest(StrictSchema):
    analysis_context: AnalysisContext
    schema_mapping: AppliedSchemaMapping
    data_quality: DataQualitySummary
    metrics: GrowthMetrics
    funnel: FunnelAnalysis
    channels: dict[str, GrowthMetrics]


class KeyFinding(StrictSchema):
    issue: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    recommendation: str = Field(min_length=1)


class ChannelStrategy(StrictSchema):
    channel: str = Field(min_length=1)
    diagnosis: str = Field(min_length=1)
    strategy: str = Field(min_length=1)


class GrowthAction(StrictSchema):
    action: str = Field(min_length=1)
    target_metric: str = Field(min_length=1)
    expected_direction: ExpectedDirection


class AIReportResponse(StrictSchema):
    summary: str = Field(min_length=1)
    key_findings: list[KeyFinding] = Field(min_length=2, max_length=3)
    channel_strategy: list[ChannelStrategy] = Field(
        min_length=1,
    )
    growth_actions: list[GrowthAction] = Field(
        min_length=2,
        max_length=3,
    )
