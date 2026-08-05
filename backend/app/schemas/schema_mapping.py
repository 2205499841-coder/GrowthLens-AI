from typing import Literal

from pydantic import BaseModel, ConfigDict


MappingConfidence = Literal["high", "medium", "low"]


class SchemaMappingResponse(BaseModel):
    """Validated semantic mapping from uploaded columns to growth fields."""

    model_config = ConfigDict(extra="forbid")

    mapping: dict[str, str | None]
    confidence: dict[str, MappingConfidence | None]
    unmapped_columns: list[str]
