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
    assert set(payload) == {"data_quality", "metrics", "funnel", "channels"}
    assert payload["data_quality"]["original_user_count"] == 3
    assert payload["data_quality"]["valid_user_count"] == 3
    assert payload["metrics"]["user_counts"]["registered_users"] == 3
    assert payload["metrics"]["user_counts"]["paid_users"] == 1
    assert payload["metrics"]["conversion_rates"]["view_rate"] == 0.6667
    assert payload["metrics"]["revenue"]["gmv"] == 1599
    assert len(payload["funnel"]["stages"]) == 6
    assert set(payload["channels"]) == {"小红书", "微信", "自然流量"}


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
