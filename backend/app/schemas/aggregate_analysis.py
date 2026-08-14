from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AnalysisStatus = Literal["ready", "partial"]
ConfidenceLevel = Literal["high", "medium", "low"]
MetricRole = Literal[
    "count_metric",
    "rate_metric",
    "amount_metric",
    "comparison_metric",
]
MetricUnit = Literal[
    "count",
    "ratio",
    "currency",
    "currency_per_order",
    "absolute",
    "percentage_point",
]
AggregationType = Literal[
    "sum",
    "weighted_rate",
    "non_additive",
]
ComparisonType = Literal[
    "yoy",
    "mom",
    "absolute_change",
    "percentage_point_change",
]
DiagnosticSeverity = Literal["high", "medium", "low"]


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AggregateMetadata(StrictSchema):
    file_name: str
    data_start_date: None = None
    data_end_date: None = None


class AggregateDataset(StrictSchema):
    dataset_type: Literal["aggregate_metrics"] = "aggregate_metrics"
    analysis_status: AnalysisStatus
    sheet_name: str
    header_rows: list[int]
    grain: list[str]
    report_period: str | None
    filters: dict[str, str]


class DimensionDefinition(StrictSchema):
    source_column: str
    label: str
    semantic_key: str
    confidence: ConfidenceLevel


class MetricDefinition(StrictSchema):
    source_column: str
    label: str
    metric_key: str
    role: MetricRole
    unit: MetricUnit
    aggregation: AggregationType
    confidence: ConfidenceLevel


class FunnelStageDefinition(StrictSchema):
    metric_key: str
    label: str
    stage_order: int = Field(ge=0)
    source_column: str
    confidence: ConfidenceLevel


class ComparisonDefinition(StrictSchema):
    source_column: str
    label: str
    comparison_type: ComparisonType
    period: Literal["yoy", "mom"] | None
    unit: Literal[
        "ratio_change",
        "percentage_point",
        "absolute_change",
        "absolute_value",
    ]
    value_kind: Literal["delta", "baseline"]
    target_metric_key: str | None
    confidence: ConfidenceLevel


class AggregateDataQuality(StrictSchema):
    row_count: int = Field(ge=0)
    detail_row_count: int = Field(ge=0)
    total_row_detected: bool
    recognized_column_count: int = Field(ge=0)
    unrecognized_columns: list[str]
    warnings: list[str]


class AggregateKPI(StrictSchema):
    metric_key: str
    label: str
    value: int | float
    unit: MetricUnit
    aggregation: AggregationType
    source: Literal["total_row", "single_row", "safe_sum", "derived"]


class AggregateFunnelStage(StrictSchema):
    metric_key: str
    label: str
    user_count: int
    conversion_rate_from_previous: float | None
    dropoff_count: int | None
    yoy: float | None
    mom: float | None
    yoy_unit: Literal[
        "ratio_change",
        "percentage_point",
        "absolute_change",
    ] | None
    mom_unit: Literal[
        "ratio_change",
        "percentage_point",
        "absolute_change",
    ] | None


class AggregateFunnel(StrictSchema):
    scope_dimension_value: str | None
    stages: list[AggregateFunnelStage]


class DimensionPerformance(StrictSchema):
    dimension_value: str
    traffic_users: int | None
    appointment_users: int | None
    payment_users: int | None
    conversion_rate: float | None
    gmv: float | None
    average_order_value: float | None
    yoy: float | None
    mom: float | None
    yoy_unit: Literal[
        "ratio_change",
        "percentage_point",
        "absolute_change",
    ] | None
    mom_unit: Literal[
        "ratio_change",
        "percentage_point",
        "absolute_change",
    ] | None


class AggregateDiagnostic(StrictSchema):
    diagnostic_type: Literal[
        "high_traffic_low_conversion",
        "high_conversion_low_traffic",
        "yoy_decline",
        "mom_decline",
        "funnel_dropoff",
        "gmv_payment_mismatch",
    ]
    title: str
    evidence: str
    severity: DiagnosticSeverity
    dimension_value: str | None
    metric_key: str | None


class AggregateOpportunity(StrictSchema):
    opportunity_type: Literal[
        "scale_high_conversion",
        "high_gmv",
        "conversion_improvement",
    ]
    title: str
    evidence: str
    dimension_value: str
    metric_key: str


class AggregateAnalysisResponse(StrictSchema):
    dataset_type: Literal["aggregate_metrics"] = "aggregate_metrics"
    analysis_status: AnalysisStatus
    metadata: AggregateMetadata
    dataset: AggregateDataset
    dimensions: list[DimensionDefinition]
    metrics: list[MetricDefinition]
    funnel_stages: list[FunnelStageDefinition]
    comparisons: list[ComparisonDefinition]
    data_quality: AggregateDataQuality
    kpis: list[AggregateKPI]
    funnel: AggregateFunnel
    dimension_performance: list[DimensionPerformance]
    diagnostics: list[AggregateDiagnostic]
    opportunities: list[AggregateOpportunity]
