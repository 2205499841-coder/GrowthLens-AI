from datetime import datetime, timedelta

import pandas as pd

from app.services.data_cleaner import clean_growth_data
from app.services.growth_metrics import build_growth_analysis


def test_calculate_metrics_funnel_and_channels() -> None:
    base_time = datetime(2026, 6, 1, 10, 0)
    data_frame = pd.DataFrame(
        [
            _row(
                user_id="U001",
                channel="小红书",
                base_time=base_time,
                paid=True,
                order_amount=1299,
            ),
            _row(
                user_id="U002",
                channel="小红书",
                base_time=base_time,
                viewed=False,
            ),
            _row(
                user_id="U003",
                channel="微信",
                base_time=base_time,
                paid=True,
                order_amount=2399,
            ),
        ]
    )

    analysis = build_growth_analysis(
        clean_growth_data(data_frame),
        file_name="metrics.xlsx",
    )
    assert analysis["metadata"] == {
        "file_name": "metrics.xlsx",
        "data_start_date": base_time.date(),
        "data_end_date": (base_time + timedelta(days=2, hours=1)).date(),
    }
    counts = analysis["metrics"]["user_counts"]
    rates = analysis["metrics"]["conversion_rates"]
    revenue = analysis["metrics"]["revenue"]

    assert counts == {
        "registered_users": 3,
        "viewed_users": 2,
        "lead_users": 2,
        "appointment_users": 2,
        "visit_users": 2,
        "paid_users": 2,
    }
    assert rates["view_rate"] == 0.6667
    assert rates["paid_rate"] == 1.0
    assert revenue == {"gmv": 3698.0, "average_order_value": 1849.0}
    assert analysis["funnel"]["stages"][1]["dropoff_count"] == 1
    assert set(analysis["channels"]) == {"小红书", "微信"}
    assert (
        analysis["channels"]["微信"]["revenue"]["average_order_value"]
        > analysis["channels"]["小红书"]["revenue"]["average_order_value"]
    )


def _row(
    *,
    user_id: str,
    channel: str,
    base_time: datetime,
    viewed: bool = True,
    paid: bool = False,
    order_amount: float | None = None,
) -> dict[str, object]:
    view_time = base_time + timedelta(minutes=5) if viewed else None
    lead_time = base_time + timedelta(minutes=10) if viewed else None
    appointment_time = base_time + timedelta(days=1) if viewed else None
    visit_time = base_time + timedelta(days=2) if viewed else None
    pay_time = (
        base_time + timedelta(days=2, hours=1)
        if viewed and paid
        else None
    )
    return {
        "user_id": user_id,
        "channel": channel,
        "register_time": base_time,
        "view_time": view_time,
        "lead_time": lead_time,
        "appointment_time": appointment_time,
        "visit_time": visit_time,
        "pay_time": pay_time,
        "order_amount": order_amount,
    }
