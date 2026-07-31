from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.ai_report import AIReportRequest
from app.services.ai_report import (
    AIReportProviderError,
    MockAIReportProvider,
    build_model_input,
    generate_ai_report,
)
from app.services.data_cleaner import clean_growth_data
from app.services.growth_metrics import build_growth_analysis


SAMPLE_FILE = (
    Path(__file__).resolve().parents[2]
    / "sample_data"
    / "portrait_growth_demo.xlsx"
)
client = TestClient(app)


def test_ai_report_endpoint_returns_structured_mock_report() -> None:
    request = _sample_request()

    response = client.post(
        "/api/ai/report",
        json=request.model_dump(mode="json"),
    )

    assert response.status_code == 200
    report = response.json()
    assert set(report) == {
        "summary",
        "key_insights",
        "channel_opportunities",
        "growth_actions",
        "limitations",
    }
    assert 2 <= len(report["key_insights"]) <= 3
    assert 2 <= len(report["growth_actions"]) <= 3
    assert {
        insight["confidence"]
        for insight in report["key_insights"]
    } <= {"high", "medium", "low"}
    assert {
        item["channel"]
        for item in report["channel_opportunities"]
    } <= set(request.channels)
    assert {
        action["expected_direction"]
        for action in report["growth_actions"]
    } <= {"increase", "decrease", "maintain"}


def test_model_input_contains_only_aggregated_analysis_results() -> None:
    model_input = build_model_input(_sample_request())

    assert '"data_quality"' in model_input
    assert '"metrics"' in model_input
    assert '"funnel"' in model_input
    assert '"channels"' in model_input
    assert '"metadata"' not in model_input
    assert '"user_id"' not in model_input
    assert '"register_time"' not in model_input
    assert SAMPLE_FILE.name not in model_input


def test_ai_report_request_rejects_extra_raw_data_fields() -> None:
    payload = _sample_request().model_dump(mode="json")
    payload["raw_rows"] = [{"user_id": "U001"}]

    response = client.post("/api/ai/report", json=payload)

    assert response.status_code == 422


def test_report_rejects_channel_not_present_in_input() -> None:
    request = _sample_request()
    valid_report = MockAIReportProvider().generate(request)
    invalid_opportunity = valid_report.channel_opportunities[0].model_copy(
        update={"channel": "虚构渠道"}
    )
    invalid_report = valid_report.model_copy(
        update={"channel_opportunities": [invalid_opportunity]}
    )

    class InvalidProvider:
        name = "invalid"

        def generate(self, request: AIReportRequest):
            return invalid_report

    with pytest.raises(
        AIReportProviderError,
        match="AI 报告引用了未知渠道",
    ):
        generate_ai_report(request, provider=InvalidProvider())


def _sample_request() -> AIReportRequest:
    data_frame = pd.read_excel(SAMPLE_FILE, engine="openpyxl")
    analysis = build_growth_analysis(
        clean_growth_data(data_frame),
        file_name=SAMPLE_FILE.name,
    )
    return AIReportRequest.model_validate(
        {
            key: analysis[key]
            for key in (
                "data_quality",
                "metrics",
                "funnel",
                "channels",
            )
        }
    )
