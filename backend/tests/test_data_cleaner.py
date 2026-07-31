from datetime import datetime, timedelta

import pandas as pd

from app.services.data_cleaner import clean_growth_data


BASE_TIME = datetime(2026, 6, 1, 10, 0)


def test_clean_data_and_calculate_growth_metrics() -> None:
    data_frame = pd.DataFrame(
        [
            _row(
                user_id="U001",
                view_time=BASE_TIME + timedelta(minutes=5),
            ),
            _row(
                user_id=" U001 ",
                view_time=BASE_TIME + timedelta(minutes=5),
                lead_time=BASE_TIME + timedelta(minutes=10),
                appointment_time=BASE_TIME + timedelta(days=1),
                visit_time=BASE_TIME + timedelta(days=2),
                pay_time=BASE_TIME + timedelta(days=2, hours=1),
                order_amount=1299,
            ),
            _row(user_id=" "),
            _row(
                user_id="U002",
                channel=" ",
                view_time=BASE_TIME - timedelta(minutes=5),
                order_amount=-100,
            ),
        ]
    )

    cleaning_result = clean_growth_data(data_frame)
    quality = cleaning_result.data_quality_summary

    assert quality["original_user_count"] == 4
    assert quality["valid_user_count"] == 2
    assert quality["removed_count"] == 2
    assert quality["anomaly_count"] == 3
    assert quality["data_completeness"] == 0.8571
    assert quality["issue_counts"]["missing_user_id"] == 1
    assert quality["issue_counts"]["duplicate_user_id"] == 1
    assert quality["issue_counts"]["unknown_channel"] == 1
    assert quality["issue_counts"]["invalid_event_order"] == 1
    assert quality["issue_counts"]["negative_amount"] == 1

    cleaned = cleaning_result.data_frame.set_index("user_id")
    assert len(cleaned) == 2
    assert cleaned.loc["U001", "order_amount"] == 1299
    assert cleaned.loc["U002", "channel"] == "未知"
    assert pd.isna(cleaned.loc["U002", "view_time"])
    assert cleaned.loc["U002", "order_amount"] == 0

def _row(
    *,
    user_id: str | None,
    channel: str = "小红书",
    register_time: datetime | None = BASE_TIME,
    view_time: datetime | None = None,
    lead_time: datetime | None = None,
    appointment_time: datetime | None = None,
    visit_time: datetime | None = None,
    pay_time: datetime | None = None,
    order_amount: float | None = None,
) -> dict[str, object]:
    return {
        "user_id": user_id,
        "channel": channel,
        "register_time": register_time,
        "view_time": view_time,
        "lead_time": lead_time,
        "appointment_time": appointment_time,
        "visit_time": visit_time,
        "pay_time": pay_time,
        "order_amount": order_amount,
    }
