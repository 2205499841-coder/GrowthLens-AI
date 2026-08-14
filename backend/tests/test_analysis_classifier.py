import json
from types import SimpleNamespace

import pytest

from app.services.analysis_classifier import (
    DEFAULT_ANALYSIS_CONTEXT,
    DeepSeekAnalysisClassifierProvider,
    classify_analysis_context,
    classify_dataset_type,
)


SCHEMA_MAPPING = {
    "mapping": {
        "user_id": "客户编号",
        "channel": "获客来源",
    },
    "source": "ai",
}


class StaticProvider:
    name = "static"

    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls: list[tuple[dict, list[str]]] = []

    def classify(self, schema_mapping, columns):
        self.calls.append((schema_mapping, columns))
        return self.payload


@pytest.mark.parametrize(
    ("columns", "expected"),
    [
        (
            ["用户ID", "渠道", "注册时间", "支付时间"],
            "user_level",
        ),
        (
            [
                "品类",
                "浏览用户数",
                "预约用户数",
                "支付转化率",
                "环比偏差",
            ],
            "aggregate_metrics",
        ),
        (["说明", "备注"], "unsupported"),
    ],
)
def test_dataset_type_classifier_supports_foundation_routes(
    columns,
    expected,
) -> None:
    assert classify_dataset_type(columns) == expected


@pytest.mark.parametrize(
    ("analysis_type", "business_type", "recommended_metrics"),
    [
        ("user_growth", "local_service", ["注册用户数", "成交率"]),
        ("ecommerce_conversion", "ecommerce", ["加购率", "支付转化率"]),
        ("content_growth", "content", ["内容曝光量", "互动率"]),
    ],
)
def test_classifier_supports_required_analysis_types(
    analysis_type,
    business_type,
    recommended_metrics,
) -> None:
    provider = StaticProvider(
        {
            "analysis_type": analysis_type,
            "business_type": business_type,
            "recommended_metrics": recommended_metrics,
        }
    )

    result = classify_analysis_context(
        SCHEMA_MAPPING,
        [" 客户编号 ", "获客来源", "获客来源"],
        provider=provider,
    )

    assert result.analysis_type == analysis_type
    assert result.business_type == business_type
    assert result.recommended_metrics == recommended_metrics
    assert provider.calls == [
        (SCHEMA_MAPPING, ["客户编号", "获客来源"])
    ]


def test_classifier_filters_metrics_outside_catalog() -> None:
    result = classify_analysis_context(
        SCHEMA_MAPPING,
        ["客户编号"],
        provider=StaticProvider(
            {
                "analysis_type": "content_growth",
                "business_type": "content",
                "recommended_metrics": [
                    "互动率",
                    "虚构指标",
                    "互动率",
                ],
            }
        ),
    )

    assert result.recommended_metrics == ["互动率"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {
            "analysis_type": "unknown",
            "business_type": "general",
            "recommended_metrics": [],
        },
    ],
)
def test_classifier_defaults_to_user_growth_for_invalid_output(payload) -> None:
    result = classify_analysis_context(
        SCHEMA_MAPPING,
        ["无法判断字段"],
        provider=StaticProvider(payload),
    )

    assert result == DEFAULT_ANALYSIS_CONTEXT
    assert result is not DEFAULT_ANALYSIS_CONTEXT


def test_classifier_defaults_when_provider_fails() -> None:
    class FailingProvider:
        name = "failing"

        def classify(self, _schema_mapping, _columns):
            raise RuntimeError("provider unavailable")

    result = classify_analysis_context(
        SCHEMA_MAPPING,
        ["客户编号"],
        provider=FailingProvider(),
    )

    assert result.analysis_type == "user_growth"


def test_deepseek_classifier_uses_json_output() -> None:
    payload = {
        "analysis_type": "ecommerce_conversion",
        "business_type": "ecommerce",
        "recommended_metrics": ["支付转化率", "GMV"],
    }
    fake_client = FakeDeepSeekClient(payload)
    provider = DeepSeekAnalysisClassifierProvider(
        api_key="test-key",
        model="deepseek-v4-pro",
        client=fake_client,
    )

    result = classify_analysis_context(
        SCHEMA_MAPPING,
        ["商品浏览", "加购次数", "支付金额"],
        provider=provider,
    )

    assert result.analysis_type == "ecommerce_conversion"
    call = fake_client.calls[0]
    assert call["model"] == "deepseek-v4-pro"
    assert call["response_format"] == {"type": "json_object"}
    assert call["extra_body"] == {"thinking": {"type": "disabled"}}
    model_input = json.loads(call["messages"][1]["content"])
    assert model_input["schema_mapping"] == SCHEMA_MAPPING
    assert model_input["columns"] == ["商品浏览", "加购次数", "支付金额"]


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
