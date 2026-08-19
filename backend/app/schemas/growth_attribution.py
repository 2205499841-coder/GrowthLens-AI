from typing import Literal

from pydantic import BaseModel, ConfigDict


Trend = Literal["growth", "decline", "stable", "unavailable"]
GrowthDriver = Literal[
    "traffic",
    "conversion",
    "combined",
    "mixed",
    "unavailable",
]
ContributionDirection = Literal[
    "positive",
    "negative",
    "neutral",
    "unavailable",
]
ChangeUnit = Literal["ratio_change", "absolute_change"]


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ScaleMetricChange(StrictSchema):
    metric_key: str
    label: str
    current_value: int | None
    yoy_change: float | None
    yoy_unit: ChangeUnit | None
    mom_change: float | None
    mom_unit: ChangeUnit | None


class TrafficChange(StrictSchema):
    browse_users_yoy: float | None
    booking_users_yoy: float | None
    payment_users_yoy: float | None
    unit: Literal["ratio_change"] | None


class ConversionChange(StrictSchema):
    payment_rate_change: float | None
    unit: Literal["ratio_change", "percentage_point"] | None


class UserScaleAnalysis(StrictSchema):
    traffic_trend: Trend
    booking_user_trend: Trend
    payment_user_trend: Trend
    scale_contribution: ContributionDirection


class FunnelContributionAnalysis(StrictSchema):
    primary_contribution_stage: str | None
    primary_drag_stage: str | None
    weakest_stage: str | None


class DimensionGrowthAttribution(StrictSchema):
    dimension_value: str
    traffic_change: TrafficChange
    conversion_change: ConversionChange
    user_scale_analysis: UserScaleAnalysis
    funnel_contribution_analysis: FunnelContributionAnalysis
    growth_driver: GrowthDriver
    driver_explanation: str
    limitations: list[str]
