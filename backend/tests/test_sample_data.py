from pathlib import Path

import pandas as pd

from app.services.data_cleaner import clean_growth_data
from app.services.excel_parser import REQUIRED_COLUMNS
from app.services.growth_metrics import build_growth_analysis


CORE_CHANNELS = ("小红书", "抖音", "微信", "自然流量")
SAMPLE_FILE = (
    Path(__file__).resolve().parents[2]
    / "sample_data"
    / "portrait_growth_demo.xlsx"
)


def test_sample_workbook_has_expected_shape_and_channels() -> None:
    data_frame = pd.read_excel(SAMPLE_FILE, engine="openpyxl")

    assert len(data_frame) == 1000
    assert tuple(data_frame.columns) == REQUIRED_COLUMNS
    assert set(CORE_CHANNELS).issubset(
        set(data_frame["channel"].dropna().str.strip())
    )


def test_sample_workbook_exposes_channel_quality_differences() -> None:
    data_frame = pd.read_excel(SAMPLE_FILE, engine="openpyxl")
    analysis = build_growth_analysis(clean_growth_data(data_frame))
    channels = analysis["channels"]
    total_counts = analysis["metrics"]["user_counts"]

    assert (
        channels["小红书"]["user_counts"]["registered_users"]
        > channels["自然流量"]["user_counts"]["registered_users"]
    )
    assert (
        channels["抖音"]["conversion_rates"]["paid_rate"]
        < channels["微信"]["conversion_rates"]["paid_rate"]
    )
    assert (
        channels["自然流量"]["revenue"]["average_order_value"]
        > channels["小红书"]["revenue"]["average_order_value"]
    )
    assert (
        total_counts["appointment_users"]
        > total_counts["visit_users"]
    )
