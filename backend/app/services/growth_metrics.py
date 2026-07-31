from typing import Any

import pandas as pd

from app.services.data_cleaner import (
    CORE_CHANNELS,
    TIME_COLUMNS,
    CleaningResult,
)


FUNNEL_STAGES = (
    ("registered_users", "注册", "register_time"),
    ("viewed_users", "浏览", "view_time"),
    ("lead_users", "留资", "lead_time"),
    ("appointment_users", "预约", "appointment_time"),
    ("visit_users", "到店", "visit_time"),
    ("paid_users", "成交", "pay_time"),
)


def build_growth_analysis(
    cleaning_result: CleaningResult,
    *,
    file_name: str,
) -> dict[str, Any]:
    data_frame = cleaning_result.data_frame
    metrics = calculate_metrics(data_frame)
    return {
        "metadata": build_analysis_metadata(data_frame, file_name),
        "data_quality": cleaning_result.data_quality_summary,
        "metrics": metrics,
        "funnel": build_funnel(metrics),
        "channels": build_channel_analysis(data_frame),
    }


def build_analysis_metadata(
    data_frame: pd.DataFrame,
    file_name: str,
) -> dict[str, Any]:
    timestamp_values = pd.concat(
        [data_frame[column].dropna() for column in TIME_COLUMNS],
        ignore_index=True,
    )
    if timestamp_values.empty:
        data_start_date = None
        data_end_date = None
    else:
        data_start_date = timestamp_values.min().date()
        data_end_date = timestamp_values.max().date()

    return {
        "file_name": file_name,
        "data_start_date": data_start_date,
        "data_end_date": data_end_date,
    }


def calculate_metrics(data_frame: pd.DataFrame) -> dict[str, Any]:
    stage_masks = _build_stage_masks(data_frame)
    user_counts = {
        stage_key: int(stage_masks[stage_key].sum())
        for stage_key, _, _ in FUNNEL_STAGES
    }
    conversion_rates = {
        "view_rate": _safe_rate(
            user_counts["viewed_users"],
            user_counts["registered_users"],
        ),
        "lead_rate": _safe_rate(
            user_counts["lead_users"],
            user_counts["viewed_users"],
        ),
        "appointment_rate": _safe_rate(
            user_counts["appointment_users"],
            user_counts["lead_users"],
        ),
        "visit_rate": _safe_rate(
            user_counts["visit_users"],
            user_counts["appointment_users"],
        ),
        "paid_rate": _safe_rate(
            user_counts["paid_users"],
            user_counts["visit_users"],
        ),
    }

    paid_mask = stage_masks["paid_users"]
    gmv = round(float(data_frame.loc[paid_mask, "order_amount"].sum()), 2)
    average_order_value = (
        round(gmv / user_counts["paid_users"], 2)
        if user_counts["paid_users"]
        else 0.0
    )
    return {
        "user_counts": user_counts,
        "conversion_rates": conversion_rates,
        "revenue": {
            "gmv": gmv,
            "average_order_value": average_order_value,
        },
    }


def build_funnel(metrics: dict[str, Any]) -> dict[str, Any]:
    counts = metrics["user_counts"]
    stages: list[dict[str, Any]] = []
    previous_count: int | None = None

    for stage_key, label, _ in FUNNEL_STAGES:
        current_count = counts[stage_key]
        if previous_count is None:
            conversion_rate = 1.0 if current_count else 0.0
            dropoff_count = 0
            dropoff_rate = 0.0
        else:
            conversion_rate = _safe_rate(current_count, previous_count)
            dropoff_count = previous_count - current_count
            dropoff_rate = _safe_rate(dropoff_count, previous_count)

        stages.append(
            {
                "key": stage_key,
                "label": label,
                "user_count": current_count,
                "conversion_rate_from_previous": conversion_rate,
                "dropoff_count": dropoff_count,
                "dropoff_rate": dropoff_rate,
            }
        )
        previous_count = current_count

    return {"stages": stages}


def build_channel_analysis(data_frame: pd.DataFrame) -> dict[str, Any]:
    channel_names = list(data_frame["channel"].dropna().unique())
    ordered_channels = [
        channel
        for channel in CORE_CHANNELS
        if channel in channel_names
    ]
    ordered_channels.extend(
        sorted(
            channel
            for channel in channel_names
            if channel not in ordered_channels
        )
    )

    return {
        channel: calculate_metrics(
            data_frame.loc[data_frame["channel"] == channel].copy()
        )
        for channel in ordered_channels
    }


def _build_stage_masks(
    data_frame: pd.DataFrame,
) -> dict[str, pd.Series]:
    masks: dict[str, pd.Series] = {}
    previous_mask = pd.Series(True, index=data_frame.index, dtype=bool)

    for stage_key, _, timestamp_column in FUNNEL_STAGES:
        current_mask = previous_mask & data_frame[timestamp_column].notna()
        masks[stage_key] = current_mask
        previous_mask = current_mask

    return masks


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)
