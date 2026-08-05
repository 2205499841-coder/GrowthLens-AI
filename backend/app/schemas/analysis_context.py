from typing import Literal

from pydantic import BaseModel, ConfigDict


AnalysisType = Literal[
    "user_growth",
    "ecommerce_conversion",
    "content_growth",
]
BusinessType = Literal[
    "general",
    "local_service",
    "ecommerce",
    "content",
]


class AnalysisContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_type: AnalysisType
    business_type: BusinessType
    recommended_metrics: list[str]
