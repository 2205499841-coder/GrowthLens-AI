from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.growth_attribution import GrowthDriver, Trend


DiagnosisPattern = Literal[
    "traffic_down_conversion_up",
    "traffic_up_conversion_down",
    "traffic_up_conversion_up",
    "traffic_down_conversion_down",
    "conversion_up_payment_down",
    "traffic_up_payment_flat",
    "funnel_front_loss",
    "funnel_mid_loss",
    "funnel_late_loss",
    "cross_metric_contradiction",
    "yoy_up_mom_down",
    "high_traffic_low_conversion",
    "low_traffic_high_conversion",
    "mixed",
]
MetricChangeUnit = Literal[
    "ratio_change",
    "percentage_point",
    "absolute_change",
]


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MetricDiagnosisContext(StrictSchema):
    metric_key: str
    label: str
    current_value: int | float | None
    yoy_change: float | None
    yoy_unit: MetricChangeUnit | None
    mom_change: float | None
    mom_unit: MetricChangeUnit | None
    trend: Trend
    evidence_refs: list[str]
    peer_median_value: float | None = None
    rank: int | None = Field(default=None, ge=1)


class FunnelStageDiagnosisContext(StrictSchema):
    from_metric_key: str
    from_label: str
    to_metric_key: str
    to_label: str
    current_conversion_rate: float | None
    yoy_delta: float | None
    mom_delta: float | None
    yoy_unit: Literal["ratio_change", "percentage_point"] | None
    mom_unit: Literal["ratio_change", "percentage_point"] | None
    peer_median_conversion_rate: float | None
    deviation_from_median: float | None
    bottleneck_score: float = Field(ge=0)
    evidence_refs: list[str]


class BottleneckDiagnosis(StrictSchema):
    stage: str
    stage_group: Literal["front", "mid", "late"]
    current_conversion_rate: float | None
    peer_median_conversion_rate: float | None
    deviation_from_median: float | None
    yoy_delta: float | None
    mom_delta: float | None
    yoy_unit: Literal["ratio_change", "percentage_point"] | None
    mom_unit: Literal["ratio_change", "percentage_point"] | None
    evidence_refs: list[str]


class DiagnosisSignal(StrictSchema):
    signal_type: str
    description: str
    evidence_refs: list[str]


class PriorityFactors(StrictSchema):
    outcome_deterioration: float = Field(ge=0)
    traffic_scale: float = Field(ge=0)
    payment_scale: float = Field(ge=0)
    funnel_deviation: float = Field(ge=0)
    yoy_deterioration: float = Field(ge=0)
    mom_deterioration: float = Field(ge=0)
    contradiction: float = Field(ge=0)
    growth_opportunity: float = Field(ge=0)


class OutcomeMetricContext(StrictSchema):
    metric_key: str
    label: str
    value: int | float
    unit: str
    evidence_ref: str


class CrossMetricDiagnosis(StrictSchema):
    dimension_value: str
    business_state: str
    outcome_state: str
    traffic_state: str
    conversion_state: str
    payment_state: str
    traffic: MetricDiagnosisContext
    booking: MetricDiagnosisContext
    payment: MetricDiagnosisContext
    conversion: MetricDiagnosisContext
    funnel: list[FunnelStageDiagnosisContext]
    attribution_driver: GrowthDriver
    driver_explanation: str
    primary_bottleneck: BottleneckDiagnosis | None
    secondary_signal: DiagnosisSignal | None
    diagnosis_patterns: list[DiagnosisPattern]
    outcome_metrics: list[OutcomeMetricContext]
    priority_score: float = Field(ge=0, le=100)
    priority_level: Literal["high", "medium", "low"]
    priority_factors: PriorityFactors
    evidence_refs: list[str]
    limitations: list[str]


class CrossMetricSummary(StrictSchema):
    scope: Literal["safe_overall", "dimension_only"]
    top_priority_dimensions: list[str]
    dominant_growth_driver: GrowthDriver
    common_bottleneck: str | None
    dimension_count: int = Field(ge=0)
