from datetime import datetime
from typing import TypeAlias

from pydantic import BaseModel, Field


CellValue: TypeAlias = str | int | float | bool | datetime | None


class ColumnProfile(BaseModel):
    name: str
    inferred_type: str
    non_null_count: int = Field(ge=0)
    null_count: int = Field(ge=0)


class ExcelParseResponse(BaseModel):
    file_name: str
    sheet_name: str
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    columns: list[ColumnProfile]
    preview: list[dict[str, CellValue]]
