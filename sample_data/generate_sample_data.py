"""Generate reproducible, synthetic user-level growth example data."""

from datetime import datetime, timedelta
from pathlib import Path
import random

import pandas as pd


OUTPUT_PATH = Path(__file__).with_name(
    "growthlens_synthetic_user_growth.xlsx"
)
RANDOM_SEED = 20260731
CHANNEL_CONFIG = {
    "小红书": {
        "count": 380,
        "rates": (0.82, 0.42, 0.48, 0.56, 0.46),
        "order_range": (799, 2199),
    },
    "抖音": {
        "count": 320,
        "rates": (0.76, 0.30, 0.40, 0.48, 0.38),
        "order_range": (599, 1699),
    },
    "微信": {
        "count": 180,
        "rates": (0.90, 0.62, 0.68, 0.76, 0.72),
        "order_range": (999, 2999),
    },
    "自然流量": {
        "count": 120,
        "rates": (0.93, 0.72, 0.76, 0.83, 0.80),
        "order_range": (1299, 3699),
    },
}


def generate_demo_data() -> pd.DataFrame:
    rng = random.Random(RANDOM_SEED)
    channels = [
        channel
        for channel, config in CHANNEL_CONFIG.items()
        for _ in range(config["count"])
    ]
    rng.shuffle(channels)

    rows: list[dict[str, object]] = []
    start_time = datetime(2026, 5, 1, 8, 0)
    for index, channel in enumerate(channels, start=1):
        config = CHANNEL_CONFIG[channel]
        register_time = start_time + timedelta(
            minutes=rng.randint(0, 75 * 24 * 60)
        )
        stage_times: list[datetime | None] = []
        previous_time = register_time

        for stage_index, rate in enumerate(config["rates"]):
            if rng.random() > rate:
                stage_times.extend(
                    [None] * (len(config["rates"]) - stage_index)
                )
                break

            if stage_index < 2:
                delay = timedelta(minutes=rng.randint(3, 360))
            elif stage_index == 2:
                delay = timedelta(hours=rng.randint(2, 72))
            else:
                delay = timedelta(hours=rng.randint(12, 120))
            previous_time += delay
            stage_times.append(previous_time)

        pay_time = stage_times[4]
        order_amount = (
            _sample_order_amount(
                rng,
                config["order_range"][0],
                config["order_range"][1],
            )
            if pay_time
            else None
        )
        rows.append(
            {
                "user_id": f"U{index:06d}",
                "channel": channel,
                "register_time": register_time,
                "view_time": stage_times[0],
                "lead_time": stage_times[1],
                "appointment_time": stage_times[2],
                "visit_time": stage_times[3],
                "pay_time": pay_time,
                "order_amount": order_amount,
            }
        )

    data_frame = pd.DataFrame(rows)
    _inject_quality_cases(data_frame, rng)
    return data_frame


def _sample_order_amount(
    rng: random.Random,
    minimum: int,
    maximum: int,
) -> int:
    raw_amount = rng.randint(minimum // 100, maximum // 100) * 100 + 99
    return min(raw_amount, maximum)


def _inject_quality_cases(
    data_frame: pd.DataFrame,
    rng: random.Random,
) -> None:
    available = set(data_frame.index)

    missing_id_rows = set(rng.sample(sorted(available), 3))
    available -= missing_id_rows
    data_frame.loc[list(missing_id_rows), "user_id"] = None

    duplicate_rows = set(rng.sample(sorted(available), 5))
    available -= duplicate_rows
    duplicate_targets = rng.sample(range(0, 100), 5)
    for duplicate_row, target_row in zip(
        sorted(duplicate_rows),
        duplicate_targets,
        strict=True,
    ):
        data_frame.at[duplicate_row, "user_id"] = data_frame.at[
            target_row,
            "user_id",
        ]

    blank_channel_rows = set(rng.sample(sorted(available), 6))
    available -= blank_channel_rows
    for row_index in blank_channel_rows:
        data_frame.at[row_index, "channel"] = "  "

    paid_rows = [
        row_index
        for row_index in available
        if pd.notna(data_frame.at[row_index, "pay_time"])
    ]
    negative_amount_rows = set(rng.sample(paid_rows, 4))
    available -= negative_amount_rows
    data_frame.loc[list(negative_amount_rows), "order_amount"] = -299

    invalid_time_rows = set(rng.sample(sorted(available), 3))
    available -= invalid_time_rows
    data_frame["view_time"] = data_frame["view_time"].astype(object)
    data_frame.loc[list(invalid_time_rows), "view_time"] = "not-a-date"

    appointment_rows = [
        row_index
        for row_index in available
        if pd.notna(data_frame.at[row_index, "appointment_time"])
    ]
    reversed_time_rows = set(rng.sample(appointment_rows, 4))
    available -= reversed_time_rows
    for row_index in reversed_time_rows:
        data_frame.at[row_index, "appointment_time"] = (
            data_frame.at[row_index, "register_time"] - timedelta(days=1)
        )

    future_payment_rows = [
        row_index
        for row_index in available
        if pd.notna(data_frame.at[row_index, "pay_time"])
    ]
    for row_index in rng.sample(future_payment_rows, 2):
        data_frame.at[row_index, "pay_time"] = datetime(2099, 1, 1, 12, 0)


def main() -> None:
    data_frame = generate_demo_data()
    data_frame.to_excel(
        OUTPUT_PATH,
        index=False,
        sheet_name="用户增长数据",
        engine="openpyxl",
    )
    print(f"Generated {len(data_frame)} rows: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
