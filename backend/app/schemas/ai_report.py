from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.analysis import (
    DataQualitySummary,
    FunnelAnalysis,
    GrowthMetrics,
)


Confidence = Literal["high", "medium", "low"]
ExpectedDirection = Literal["increase", "decrease", "maintain"]


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AIReportRequest(StrictSchema):
    data_quality: DataQualitySummary
    metrics: GrowthMetrics
    funnel: FunnelAnalysis
    channels: dict[str, GrowthMetrics]


class KeyInsight(StrictSchema):
    title: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    interpretation: str = Field(min_length=1)
    confidence: Confidence


class ChannelOpportunity(StrictSchema):
    channel: str = Field(min_length=1)
    opportunity: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    confidence: Confidence


class GrowthAction(StrictSchema):
    action: str = Field(min_length=1)
    target_metric: str = Field(min_length=1)
    expected_direction: ExpectedDirection


class AIReportResponse(StrictSchema):
    summary: str = Field(min_length=1)
    key_insights: list[KeyInsight] = Field(min_length=2, max_length=3)
    channel_opportunities: list[ChannelOpportunity] = Field(
        min_length=1,
    )
    growth_actions: list[GrowthAction] = Field(
        min_length=2,
        max_length=3,
    )
    limitations: list[str] = Field(min_length=1)
