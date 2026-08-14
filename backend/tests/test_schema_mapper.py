import json
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

import app.api.uploads as uploads_api
import app.services.schema_mapper as schema_mapper_service
from app.main import app
from app.schemas.schema_mapping import SchemaMappingResponse
from app.services.excel_parser import REQUIRED_COLUMNS
from app.services.schema_mapper import (
    DeepSeekSchemaMappingProvider,
    SchemaMappingError,
    map_aggregate_columns,
    map_columns,
)


client = TestClient(app)


class FakeDeepSeekClient:
    def __init__(self, payload: dict) -> None:
        self.calls: list[dict] = []
        self._content = json.dumps(payload, ensure_ascii=False)
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create),
        )

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self._content),
                )
            ]
        )


def test_deepseek_maps_columns_with_validated_json_output() -> None:
    columns = ["客户编号", "来源渠道", "首次访问", "成交金额"]
    fake_client = FakeDeepSeekClient(
        {
            "mapping": {
                "user_id": "客户编号",
                "channel": "来源渠道",
                "visit_time": "首次访问",
                "order_amount": "成交金额",
            },
            "confidence": {
                "user_id": "high",
                "channel": "high",
                "visit_time": "medium",
                "order_amount": "high",
            },
            "unmapped_columns": [],
        }
    )
    provider = DeepSeekSchemaMappingProvider(
        api_key="test-key",
        model="deepseek-v4-pro",
        client=fake_client,
    )

    result = map_columns(columns, provider=provider)

    assert result.mapping["user_id"] == "客户编号"
    assert result.mapping["channel"] == "来源渠道"
    assert result.mapping["visit_time"] == "首次访问"
    assert result.mapping["order_amount"] == "成交金额"
    assert result.mapping["pay_time"] is None
    assert result.confidence["pay_time"] is None
    assert result.unmapped_columns == []

    assert len(fake_client.calls) == 1
    call = fake_client.calls[0]
    assert call["model"] == "deepseek-v4-pro"
    assert call["response_format"] == {"type": "json_object"}
    assert call["extra_body"] == {"thinking": {"type": "disabled"}}
    assert columns == json.loads(call["messages"][1]["content"].split("\n", 1)[1])


def test_mapper_nulls_hallucinated_and_duplicate_source_fields() -> None:
    class UnsafeProvider:
        name = "unsafe"

        def map_columns(self, _columns: list[str]) -> dict:
            return {
                "mapping": {
                    "user_id": "不存在字段",
                    "channel": "来源渠道",
                    "order_amount": "来源渠道",
                    "not_standard": "客户编号",
                },
                "confidence": {
                    "user_id": "high",
                    "channel": "high",
                    "order_amount": "high",
                    "not_standard": "high",
                },
                "unmapped_columns": [],
            }

    result = map_columns(
        ["客户编号", "来源渠道", "成交金额"],
        provider=UnsafeProvider(),
    )

    assert result.mapping["user_id"] is None
    assert result.mapping["channel"] == "来源渠道"
    assert result.mapping["order_amount"] is None
    assert "not_standard" not in result.mapping
    assert result.unmapped_columns == ["客户编号", "成交金额"]


def test_mapper_returns_null_for_unrecognized_fields() -> None:
    class UnknownProvider:
        name = "unknown"

        def map_columns(self, _columns: list[str]) -> dict:
            return {
                "mapping": {},
                "confidence": {},
                "unmapped_columns": ["备注", "客服标签"],
            }

    result = map_columns(
        ["备注", "客服标签"],
        provider=UnknownProvider(),
    )

    assert result.mapping == {field: None for field in REQUIRED_COLUMNS}
    assert result.confidence == {field: None for field in REQUIRED_COLUMNS}
    assert result.unmapped_columns == ["备注", "客服标签"]


def test_deepseek_schema_mapper_requires_api_key() -> None:
    with pytest.raises(SchemaMappingError, match="DEEPSEEK_API_KEY"):
        DeepSeekSchemaMappingProvider(
            api_key=None,
            model="deepseek-v4-pro",
        )


def test_aggregate_ai_fallback_uses_profiles_and_rejects_hallucinations(
    monkeypatch,
) -> None:
    fake_client = FakeDeepSeekClient(
        {
            "fields": [
                {
                    "source_column": "访问客户量",
                    "role": "count_metric",
                    "semantic_key": "traffic_users",
                    "confidence": "medium",
                },
                {
                    "source_column": "不存在字段",
                    "role": "amount_metric",
                    "semantic_key": "gmv",
                    "confidence": "high",
                },
            ]
        }
    )
    monkeypatch.setattr(
        schema_mapper_service,
        "settings",
        SimpleNamespace(
            ai_provider="deepseek",
            deepseek_api_key="test-key",
            ai_model="deepseek-chat",
        ),
    )
    profiles = [
        {
            "source_column": "访问客户量",
            "inferred_type": "numeric",
            "numeric_ratio": 1.0,
            "unique_ratio": 0.8,
            "percentage_format": False,
            "value_range": "zero_to_10000",
        }
    ]

    result = map_aggregate_columns(profiles, client=fake_client)

    assert result == [
        {
            "source_column": "访问客户量",
            "role": "count_metric",
            "semantic_key": "traffic_users",
            "confidence": "medium",
        }
    ]
    request_payload = json.loads(
        fake_client.calls[0]["messages"][1]["content"]
    )
    assert request_payload == {"unresolved_columns": profiles}


def test_schema_map_endpoint_selects_detail_sheet(monkeypatch) -> None:
    workbook = Workbook()
    overview = workbook.active
    overview.title = "数据概览"
    overview.append(["指标", "结果"])
    overview.append(["注册用户", 100])

    detail = workbook.create_sheet("客户明细")
    detail.append(["业务系统客户数据"])
    detail.append(["客户编号", "来源渠道", "首次访问", "成交金额"])
    detail.append(["U001", "小红书", "2026-08-01", 1299])

    file_buffer = BytesIO()
    workbook.save(file_buffer)
    captured_columns: list[str] = []

    def fake_map_columns(columns):
        captured_columns.extend(columns)
        return SchemaMappingResponse(
            mapping={
                **{field: None for field in REQUIRED_COLUMNS},
                "user_id": "客户编号",
                "channel": "来源渠道",
                "visit_time": "首次访问",
                "order_amount": "成交金额",
            },
            confidence={
                **{field: None for field in REQUIRED_COLUMNS},
                "user_id": "high",
                "channel": "high",
                "visit_time": "medium",
                "order_amount": "high",
            },
            unmapped_columns=[],
        )

    monkeypatch.setattr(uploads_api, "map_columns", fake_map_columns)
    response = client.post(
        "/api/uploads/schema-map",
        files={
            "file": (
                "custom_columns.xlsx",
                file_buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    assert captured_columns == [
        "客户编号",
        "来源渠道",
        "首次访问",
        "成交金额",
    ]
    payload = response.json()
    assert payload["mapping"]["user_id"] == "客户编号"
    assert payload["mapping"]["register_time"] is None
    assert payload["confidence"]["visit_time"] == "medium"
    assert payload["unmapped_columns"] == []
