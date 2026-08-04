from datetime import datetime, timedelta
from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.main import app
from app.services.excel_parser import REQUIRED_COLUMNS


client = TestClient(app)


def test_analyze_growth_excel_returns_unified_structure() -> None:
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
    assert payload["data_quality"]["original_user_count"] == 3
    assert payload["data_quality"]["valid_user_count"] == 3
    assert payload["metrics"]["user_counts"]["registered_users"] == 3
    assert payload["metrics"]["user_counts"]["paid_users"] == 1
    assert payload["metrics"]["conversion_rates"]["view_rate"] == 0.6667
    assert payload["metrics"]["revenue"]["gmv"] == 1599
    assert len(payload["funnel"]["stages"]) == 6
    assert set(payload["channels"]) == {"小红书", "微信", "自然流量"}


def test_analyze_growth_excel_returns_structured_ingestion_error() -> None:
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
        "error": "Excel字段不完整",
        "message": "未找到用户增长分析所需字段",
        "missing_fields": ["pay_time", "order_amount"],
        "detected_sheet_names": ["用户明细"],
        "candidate_sheet_name": "用户明细",
        "recognized_field_count": 7,
        "data_quality_status": "invalid",
    }


def _create_analysis_workbook() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "用户增长数据"
    worksheet.append(list(REQUIRED_COLUMNS))
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
