from pathlib import Path

import pandas as pd

from app.services.excel_parser import REQUIRED_COLUMNS


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
