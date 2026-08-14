from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.analysis_context import AnalysisContext
from app.schemas.ingestion import DataIngestionSummary


class AnalysisMetadata(BaseModel):
    file_name: str
    data_start_date: date | None
    data_end_date: date | None


class DataQualitySummary(BaseModel):
    original_user_count: int = Field(ge=0)
    valid_user_count: int = Field(ge=0)
    removed_count: int = Field(ge=0)
    anomaly_count: int = Field(ge=0)
    data_completeness: float = Field(ge=0, le=1)
    issue_counts: dict[str, int]


class UserCounts(BaseModel):
    registered_users: int = Field(ge=0)
    viewed_users: int | None = Field(default=None, ge=0)
    lead_users: int | None = Field(default=None, ge=0)
    appointment_users: int | None = Field(default=None, ge=0)
    visit_users: int | None = Field(default=None, ge=0)
    paid_users: int = Field(ge=0)


class ConversionRates(BaseModel):
    view_rate: float | None = Field(default=None, ge=0, le=1)
    lead_rate: float | None = Field(default=None, ge=0, le=1)
    appointment_rate: float | None = Field(default=None, ge=0, le=1)
    visit_rate: float | None = Field(default=None, ge=0, le=1)
    paid_rate: float = Field(ge=0, le=1)


class RevenueMetrics(BaseModel):
    gmv: float = Field(ge=0)
    average_order_value: float = Field(ge=0)


class GrowthMetrics(BaseModel):
    user_counts: UserCounts
    conversion_rates: ConversionRates
    revenue: RevenueMetrics


class FunnelStage(BaseModel):
    key: str
    label: str
    user_count: int = Field(ge=0)
    conversion_rate_from_previous: float = Field(ge=0, le=1)
    dropoff_count: int = Field(ge=0)
    dropoff_rate: float = Field(ge=0, le=1)


class FunnelAnalysis(BaseModel):
    stages: list[FunnelStage]


class AppliedSchemaMapping(BaseModel):
    mapping: dict[str, str]
    source: Literal["fixed", "ai"]
    missing_fields: list[str] = Field(default_factory=list)


class GrowthAnalysisResponse(BaseModel):
    dataset_type: Literal["user_level"] = "user_level"
    analysis_status: Literal["ready"] = "ready"
    metadata: AnalysisMetadata
    data_ingestion: DataIngestionSummary
    schema_mapping: AppliedSchemaMapping
    analysis_context: AnalysisContext
    data_quality: DataQualitySummary
    metrics: GrowthMetrics
    funnel: FunnelAnalysis
    channels: dict[str, GrowthMetrics]


class DatasetPlaceholderResponse(BaseModel):
    dataset_type: Literal["aggregate_metrics", "unsupported"]
    analysis_status: Literal["unavailable"] = "unavailable"
    metadata: AnalysisMetadata
    message: str
    data_ingestion: None = None
    schema_mapping: None = None
    analysis_context: None = None
    data_quality: None = None
    metrics: None = None
    funnel: None = None
    channels: None = None


AnalysisResponse = GrowthAnalysisResponse | DatasetPlaceholderResponse
