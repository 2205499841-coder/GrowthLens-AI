from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd


REQUIRED_COLUMNS = (
    "user_id",
    "channel",
    "register_time",
    "view_time",
    "lead_time",
    "appointment_time",
    "visit_time",
    "pay_time",
    "order_amount",
)


class ExcelParseError(ValueError):
    """Raised when an uploaded workbook cannot be parsed safely."""


@dataclass(frozen=True)
class ParsedExcel:
    sheet_name: str
    data_frame: pd.DataFrame


def validate_file_name(file_name: str | None) -> str:
    normalized_name = Path(file_name or "").name
    if not normalized_name:
        raise ExcelParseError("请选择需要上传的 Excel 文件。")
    if Path(normalized_name).suffix.lower() != ".xlsx":
        raise ExcelParseError("当前仅支持 .xlsx 格式的 Excel 文件。")
    return normalized_name


def parse_excel(file_content: bytes) -> ParsedExcel:
    if not file_content:
        raise ExcelParseError("上传的 Excel 文件为空。")

    try:
        workbook = pd.ExcelFile(BytesIO(file_content), engine="openpyxl")
    except Exception as exc:
        raise ExcelParseError("Excel 文件无法读取，请确认文件未损坏且格式正确。") from exc

    if not workbook.sheet_names:
        raise ExcelParseError("Excel 文件中没有可读取的工作表。")

    first_sheet = workbook.sheet_names[0]
    try:
        data_frame = workbook.parse(sheet_name=first_sheet)
    except Exception as exc:
        raise ExcelParseError("第一个工作表解析失败，请检查表格内容。") from exc

    data_frame.columns = [str(column).strip() for column in data_frame.columns]

    if data_frame.empty:
        raise ExcelParseError("第一个工作表没有数据行。")

    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in data_frame.columns
    ]
    if missing_columns:
        missing = "、".join(missing_columns)
        raise ExcelParseError(f"缺少必填字段：{missing}。请使用标准数据模板。")

    return ParsedExcel(sheet_name=first_sheet, data_frame=data_frame)


def build_parse_response(
    *,
    file_name: str,
    parsed_excel: ParsedExcel,
    preview_limit: int,
) -> dict[str, Any]:
    data_frame = parsed_excel.data_frame
    columns = [
        {
            "name": str(column),
            "inferred_type": str(data_frame[column].dtype),
            "non_null_count": int(data_frame[column].notna().sum()),
            "null_count": int(data_frame[column].isna().sum()),
        }
        for column in data_frame.columns
    ]

    preview_frame = data_frame.head(preview_limit)
    preview = [
        {
            str(column): _to_json_value(value)
            for column, value in row.items()
        }
        for row in preview_frame.to_dict(orient="records")
    ]

    return {
        "file_name": file_name,
        "sheet_name": parsed_excel.sheet_name,
        "row_count": int(len(data_frame)),
        "column_count": int(len(data_frame.columns)),
        "columns": columns,
        "preview": preview,
    }


def _to_json_value(value: Any) -> str | int | float | bool | datetime | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
