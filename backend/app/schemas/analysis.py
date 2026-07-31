from pydantic import BaseModel, Field


class DataQualitySummary(BaseModel):
    original_user_count: int = Field(ge=0)
    valid_user_count: int = Field(ge=0)
    removed_count: int = Field(ge=0)
    anomaly_count: int = Field(ge=0)
    data_completeness: float = Field(ge=0, le=1)
    issue_counts: dict[str, int]


class UserCounts(BaseModel):
    registered_users: int = Field(ge=0)
    viewed_users: int = Field(ge=0)
    lead_users: int = Field(ge=0)
    appointment_users: int = Field(ge=0)
    visit_users: int = Field(ge=0)
    paid_users: int = Field(ge=0)


class ConversionRates(BaseModel):
    view_rate: float = Field(ge=0, le=1)
    lead_rate: float = Field(ge=0, le=1)
    appointment_rate: float = Field(ge=0, le=1)
    visit_rate: float = Field(ge=0, le=1)
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


class GrowthAnalysisResponse(BaseModel):
    data_quality: DataQualitySummary
    metrics: GrowthMetrics
    funnel: FunnelAnalysis
    channels: dict[str, GrowthMetrics]
