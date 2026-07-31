from datetime import datetime
from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.main import app
from app.services.excel_parser import REQUIRED_COLUMNS


client = TestClient(app)


def create_workbook_bytes(
    *,
    columns: tuple[str, ...] = REQUIRED_COLUMNS,
    include_data_row: bool = True,
) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "用户增长数据"
    worksheet.append(list(columns))

    if include_data_row:
        values = {
            "user_id": "U10001",
            "channel": "小红书",
            "register_time": datetime(2026, 7, 1, 10, 0),
            "view_time": datetime(2026, 7, 1, 10, 5),
            "lead_time": datetime(2026, 7, 1, 10, 10),
            "appointment_time": datetime(2026, 7, 2, 14, 0),
            "visit_time": datetime(2026, 7, 5, 11, 0),
            "pay_time": datetime(2026, 7, 5, 13, 0),
            "order_amount": 1299,
        }
        worksheet.append([values.get(column) for column in columns])

    file_buffer = BytesIO()
    workbook.save(file_buffer)
    return file_buffer.getvalue()


def test_parse_valid_excel() -> None:
    response = client.post(
        "/api/uploads/parse",
        headers={"Origin": "http://127.0.0.1:3000"},
        files={
            "file": (
                "photo_growth.xlsx",
                create_workbook_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["file_name"] == "photo_growth.xlsx"
    assert payload["sheet_name"] == "用户增长数据"
    assert payload["row_count"] == 1
    assert payload["column_count"] == len(REQUIRED_COLUMNS)
    assert payload["preview"][0]["user_id"] == "U10001"
    assert payload["preview"][0]["order_amount"] == 1299
    assert (
        response.headers["access-control-allow-origin"]
        == "http://127.0.0.1:3000"
    )


def test_reject_non_xlsx_file() -> None:
    response = client.post(
        "/api/uploads/parse",
        files={"file": ("users.csv", b"user_id,channel", "text/csv")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "当前仅支持 .xlsx 格式的 Excel 文件。"


def test_report_missing_required_columns() -> None:
    response = client.post(
        "/api/uploads/parse",
        files={
            "file": (
                "missing_columns.xlsx",
                create_workbook_bytes(columns=("user_id", "channel")),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 422
    assert "缺少必填字段" in response.json()["detail"]
    assert "register_time" in response.json()["detail"]


def test_reject_workbook_without_data_rows() -> None:
    response = client.post(
        "/api/uploads/parse",
        files={
            "file": (
                "empty.xlsx",
                create_workbook_bytes(include_data_row=False),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "第一个工作表没有数据行。"
