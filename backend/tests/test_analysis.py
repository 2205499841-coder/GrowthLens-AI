from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

import app.api.analysis as analysis_api
from app.main import app
from app.schemas.schema_mapping import SchemaMappingResponse
from app.services.analysis_classifier import DEFAULT_ANALYSIS_CONTEXT
from app.services.excel_parser import REQUIRED_COLUMNS


client = TestClient(app)
SAMPLE_FILE = (
    Path(__file__).resolve().parents[2]
    / "sample_data"
    / "portrait_growth_demo.xlsx"
)


@pytest.fixture(autouse=True)
def stub_analysis_classifier(monkeypatch) -> None:
    monkeypatch.setattr(
        analysis_api,
        "classify_analysis_context",
        lambda _schema_mapping, _columns: (
            DEFAULT_ANALYSIS_CONTEXT.model_copy(deep=True)
        ),
    )


def test_analyze_growth_excel_returns_unified_structure(monkeypatch) -> None:
    def fail_if_ai_mapping_is_called(_columns):
        raise AssertionError("固定模板不应调用 AI 字段识别")

    monkeypatch.setattr(
        analysis_api,
        "map_columns",
        fail_if_ai_mapping_is_called,
    )
    response = client.post(
        "/api/analysis/growth",
        files={
            "file": (
                "growth.xlsx",
                _create_analysis_workbook(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "metadata",
        "data_ingestion",
        "schema_mapping",
        "analysis_context",
        "data_quality",
        "metrics",
        "funnel",
        "channels",
    }
    assert payload["metadata"] == {
        "file_name": "growth.xlsx",
        "data_start_date": "2026-06-01",
        "data_end_date": "2026-06-03",
    }
    assert payload["data_ingestion"]["used_sheet_name"] == "用户增长数据"
    assert payload["data_ingestion"]["recognized_field_count"] == 9
    assert payload["data_ingestion"]["missing_fields"] == []
    assert payload["schema_mapping"] == {
        "mapping": {field: field for field in REQUIRED_COLUMNS},
        "source": "fixed",
    }
    assert payload["analysis_context"] == (
        DEFAULT_ANALYSIS_CONTEXT.model_dump(mode="json")
    )
    assert payload["data_quality"]["original_user_count"] == 3
    assert payload["data_quality"]["valid_user_count"] == 3
    assert payload["metrics"]["user_counts"]["registered_users"] == 3
    assert payload["metrics"]["user_counts"]["paid_users"] == 1
    assert payload["metrics"]["conversion_rates"]["view_rate"] == 0.6667
    assert payload["metrics"]["revenue"]["gmv"] == 1599
    assert len(payload["funnel"]["stages"]) == 6
    assert set(payload["channels"]) == {"小红书", "微信", "自然流量"}


def test_portrait_demo_keeps_fixed_mapping_path(monkeypatch) -> None:
    def fail_if_ai_mapping_is_called(_columns):
        raise AssertionError("演示文件不应调用 AI 字段识别")

    monkeypatch.setattr(
        analysis_api,
        "map_columns",
        fail_if_ai_mapping_is_called,
    )
    response = client.post(
        "/api/analysis/growth",
        files={
            "file": (
                SAMPLE_FILE.name,
                SAMPLE_FILE.read_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_mapping"]["source"] == "fixed"
    assert payload["data_quality"]["original_user_count"] == 1000


def test_nonstandard_excel_uses_ai_mapping(monkeypatch) -> None:
    custom_columns = (
        "客户编号",
        "获客来源",
        "开户日期",
        "首次浏览",
        "提交线索",
        "预订日期",
        "实际到店",
        "付款日期",
        "实收金额",
    )
    mapping = dict(zip(REQUIRED_COLUMNS, custom_columns, strict=True))

    monkeypatch.setattr(
        analysis_api,
        "map_columns",
        lambda _columns: SchemaMappingResponse(
            mapping=mapping,
            confidence={field: "high" for field in REQUIRED_COLUMNS},
            unmapped_columns=[],
        ),
    )

    response = client.post(
        "/api/analysis/growth",
        files={
            "file": (
                "custom_growth.xlsx",
                _create_analysis_workbook(columns=custom_columns),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_mapping"] == {
        "mapping": mapping,
        "source": "ai",
    }
    assert payload["data_ingestion"]["field_mapping"] == mapping
    assert payload["metrics"]["user_counts"]["registered_users"] == 3
    assert payload["metrics"]["user_counts"]["paid_users"] == 1
    assert payload["metrics"]["revenue"]["gmv"] == 1599


def test_ai_mapping_cannot_reference_nonexistent_column(monkeypatch) -> None:
    custom_columns = tuple(f"自定义字段{index}" for index in range(9))
    invalid_mapping = dict(
        zip(REQUIRED_COLUMNS, custom_columns, strict=True)
    )
    invalid_mapping["order_amount"] = "AI虚构金额字段"

    monkeypatch.setattr(
        analysis_api,
        "map_columns",
        lambda _columns: SchemaMappingResponse(
            mapping=invalid_mapping,
            confidence={field: "high" for field in REQUIRED_COLUMNS},
            unmapped_columns=[],
        ),
    )
    response = client.post(
        "/api/analysis/growth",
        files={
            "file": (
                "hallucinated_mapping.xlsx",
                _create_analysis_workbook(columns=custom_columns),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 422
    assert response.json()["error"] == "AI字段映射无效"
    assert response.json()["missing_fields"] == ["AI虚构金额字段"]


def test_ai_unrecognized_fields_returns_structured_error(monkeypatch) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "用户明细"
    worksheet.append(list(REQUIRED_COLUMNS[:-2]))
    base_time = datetime(2026, 6, 1, 10, 0)
    worksheet.append(
        [
            "U001",
            "小红书",
            base_time,
            base_time + timedelta(minutes=5),
            base_time + timedelta(minutes=10),
            base_time + timedelta(days=1),
            base_time + timedelta(days=2),
        ]
    )
    file_buffer = BytesIO()
    workbook.save(file_buffer)

    monkeypatch.setattr(
        analysis_api,
        "map_columns",
        lambda _columns: SchemaMappingResponse(
            mapping={field: None for field in REQUIRED_COLUMNS},
            confidence={field: None for field in REQUIRED_COLUMNS},
            unmapped_columns=list(REQUIRED_COLUMNS[:-2]),
        ),
    )

    response = client.post(
        "/api/analysis/growth",
        files={
            "file": (
                "missing_fields.xlsx",
                file_buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "error": "AI字段映射不完整",
        "message": "AI 未能识别全部用户增长分析字段。",
        "missing_fields": list(REQUIRED_COLUMNS),
        "detected_sheet_names": ["用户明细"],
        "candidate_sheet_name": "用户明细",
        "recognized_field_count": 0,
        "data_quality_status": "invalid",
    }


def _create_analysis_workbook(
    *,
    columns: tuple[str, ...] = REQUIRED_COLUMNS,
) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "用户增长数据"
    worksheet.append(list(columns))
    base_time = datetime(2026, 6, 1, 10, 0)

    worksheet.append(
        [
            "U001",
            "小红书",
            base_time,
            base_time + timedelta(minutes=5),
            base_time + timedelta(minutes=10),
            base_time + timedelta(days=1),
            base_time + timedelta(days=2),
            base_time + timedelta(days=2, hours=1),
            1599,
        ]
    )
    worksheet.append(
        [
            "U002",
            "微信",
            base_time,
            base_time + timedelta(minutes=3),
            None,
            None,
            None,
            None,
            None,
        ]
    )
    worksheet.append(
        [
            "U003",
            "自然流量",
            base_time,
            None,
            None,
            None,
            None,
            None,
            None,
        ]
    )

    file_buffer = BytesIO()
    workbook.save(file_buffer)
    return file_buffer.getvalue()
