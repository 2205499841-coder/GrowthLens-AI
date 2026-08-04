import unicodedata
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

FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "user_id": ("user_id", "用户ID", "用户编号", "用户标识"),
    "channel": (
        "channel",
        "渠道",
        "来源渠道",
        "用户来源渠道",
        "来源",
    ),
    "register_time": ("register_time", "注册时间", "注册日期"),
    "view_time": ("view_time", "浏览时间", "查看时间", "首次访问时间"),
    "lead_time": ("lead_time", "留资时间", "咨询时间"),
    "appointment_time": ("appointment_time", "预约时间"),
    "visit_time": ("visit_time", "到店时间", "核销时间"),
    "pay_time": ("pay_time", "支付时间", "成交时间"),
    "order_amount": (
        "order_amount",
        "订单金额",
        "支付金额",
        "成交金额",
        "金额",
    ),
}


class ExcelParseError(ValueError):
    """Raised with structured evidence when a workbook cannot be ingested."""

    def __init__(
        self,
        message: str,
        *,
        error: str = "Excel解析失败",
        missing_fields: list[str] | None = None,
        detected_sheet_names: list[str] | None = None,
        candidate_sheet_name: str | None = None,
        recognized_field_count: int = 0,
    ) -> None:
        super().__init__(message)
        self.error = error
        self.message = message
        self.missing_fields = missing_fields or []
        self.detected_sheet_names = detected_sheet_names or []
        self.candidate_sheet_name = candidate_sheet_name
        self.recognized_field_count = recognized_field_count

    def to_response_payload(self) -> dict[str, Any]:
        return {
            "error": self.error,
            "message": self.message,
            "missing_fields": self.missing_fields,
            "detected_sheet_names": self.detected_sheet_names,
            "candidate_sheet_name": self.candidate_sheet_name,
            "recognized_field_count": self.recognized_field_count,
            "data_quality_status": "invalid",
        }


@dataclass(frozen=True)
class ParsedExcel:
    sheet_name: str
    data_frame: pd.DataFrame
    detected_sheet_names: tuple[str, ...]
    field_mapping: dict[str, str]

    @property
    def data_ingestion_summary(self) -> dict[str, Any]:
        return {
            "used_sheet_name": self.sheet_name,
            "detected_sheet_names": list(self.detected_sheet_names),
            "recognized_field_count": len(self.field_mapping),
            "total_required_field_count": len(REQUIRED_COLUMNS),
            "missing_fields": [],
            "row_count": int(len(self.data_frame)),
            "data_quality_status": "ready",
            "field_mapping": dict(self.field_mapping),
        }


@dataclass(frozen=True)
class _SheetCandidate:
    sheet_name: str
    sheet_index: int
    data_frame: pd.DataFrame
    field_mapping: dict[str, str]

    @property
    def recognized_field_count(self) -> int:
        return len(self.field_mapping)

    @property
    def missing_fields(self) -> list[str]:
        return [
            field for field in REQUIRED_COLUMNS if field not in self.field_mapping
        ]


def validate_file_name(file_name: str | None) -> str:
    normalized_name = Path(file_name or "").name
    if not normalized_name:
        raise ExcelParseError(
            "请选择需要上传的 Excel 文件。",
            error="Excel文件不可用",
        )
    if Path(normalized_name).suffix.lower() != ".xlsx":
        raise ExcelParseError(
            "当前仅支持 .xlsx 格式的 Excel 文件。",
            error="Excel文件格式不支持",
        )
    return normalized_name


def parse_excel(file_content: bytes) -> ParsedExcel:
    if not file_content:
        raise ExcelParseError("上传的 Excel 文件为空。", error="Excel文件不可用")

    try:
        workbook = pd.ExcelFile(BytesIO(file_content), engine="openpyxl")
    except Exception as exc:
        raise ExcelParseError(
            "Excel 文件无法读取，请确认文件未损坏且格式正确。",
            error="Excel文件不可用",
        ) from exc

    if not workbook.sheet_names:
        raise ExcelParseError(
            "Excel 文件中没有可读取的工作表。",
            error="Excel工作表不可用",
        )

    detected_sheet_names = tuple(str(name) for name in workbook.sheet_names)
    candidates: list[_SheetCandidate] = []

    for sheet_index, sheet_name in enumerate(detected_sheet_names):
        try:
            data_frame = workbook.parse(sheet_name=sheet_name)
        except Exception:
            continue

        data_frame.columns = [str(column).strip() for column in data_frame.columns]
        candidates.append(
            _SheetCandidate(
                sheet_name=sheet_name,
                sheet_index=sheet_index,
                data_frame=data_frame,
                field_mapping=_detect_field_mapping(data_frame.columns),
            )
        )

    if not candidates:
        raise ExcelParseError(
            "检测到工作表，但所有工作表都无法读取。",
            error="Excel工作表不可用",
            detected_sheet_names=list(detected_sheet_names),
        )

    best_candidate = max(
        candidates,
        key=lambda candidate: (
            candidate.recognized_field_count,
            not candidate.data_frame.empty,
            len(candidate.data_frame),
            -candidate.sheet_index,
        ),
    )

    if best_candidate.missing_fields:
        raise ExcelParseError(
            "未找到用户增长分析所需字段",
            error="Excel字段不完整",
            missing_fields=best_candidate.missing_fields,
            detected_sheet_names=list(detected_sheet_names),
            candidate_sheet_name=best_candidate.sheet_name,
            recognized_field_count=best_candidate.recognized_field_count,
        )

    if best_candidate.data_frame.empty:
        raise ExcelParseError(
            f"已识别数据 Sheet“{best_candidate.sheet_name}”，但该 Sheet 没有数据行。",
            error="Excel数据为空",
            detected_sheet_names=list(detected_sheet_names),
            candidate_sheet_name=best_candidate.sheet_name,
            recognized_field_count=best_candidate.recognized_field_count,
        )

    rename_map = {
        source_field: canonical_field
        for canonical_field, source_field in best_candidate.field_mapping.items()
    }
    mapped_data_frame = best_candidate.data_frame.rename(columns=rename_map)

    return ParsedExcel(
        sheet_name=best_candidate.sheet_name,
        data_frame=mapped_data_frame,
        detected_sheet_names=detected_sheet_names,
        field_mapping=best_candidate.field_mapping,
    )


def _normalize_field_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    return "".join(normalized.split())


def _detect_field_mapping(columns: pd.Index) -> dict[str, str]:
    alias_lookup: dict[str, tuple[str, int]] = {}
    for canonical_field, aliases in FIELD_ALIASES.items():
        for alias_priority, alias in enumerate(aliases):
            alias_lookup[_normalize_field_name(alias)] = (
                canonical_field,
                alias_priority,
            )

    selected_fields: dict[str, tuple[int, int, str]] = {}
    for column_index, source_field in enumerate(columns):
        match = alias_lookup.get(_normalize_field_name(str(source_field)))
        if match is None:
            continue

        canonical_field, alias_priority = match
        candidate = (alias_priority, column_index, str(source_field))
        current = selected_fields.get(canonical_field)
        if current is None or candidate[:2] < current[:2]:
            selected_fields[canonical_field] = candidate

    return {
        canonical_field: selected_fields[canonical_field][2]
        for canonical_field in REQUIRED_COLUMNS
        if canonical_field in selected_fields
    }


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
        "data_ingestion": parsed_excel.data_ingestion_summary,
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
