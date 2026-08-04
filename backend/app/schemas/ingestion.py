from typing import Literal

from pydantic import BaseModel, Field


class DataIngestionSummary(BaseModel):
    used_sheet_name: str
    detected_sheet_names: list[str]
    recognized_field_count: int = Field(ge=0)
    total_required_field_count: int = Field(ge=0)
    missing_fields: list[str]
    row_count: int = Field(ge=0)
    data_quality_status: Literal["ready"]
    field_mapping: dict[str, str]


class ExcelIngestionErrorResponse(BaseModel):
    error: str
    message: str
    missing_fields: list[str]
    detected_sheet_names: list[str]
    candidate_sheet_name: str | None
    recognized_field_count: int = Field(ge=0)
    data_quality_status: Literal["invalid"]
