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
    available_fields = cleaning_result.available_fields
    metrics = calculate_metrics(
        data_frame,
        available_fields=available_fields,
    )
    return {
        "metadata": build_analysis_metadata(
            data_frame,
            file_name,
            available_fields=available_fields,
        ),
        "data_quality": cleaning_result.data_quality_summary,
        "metrics": metrics,
        "funnel": build_funnel(
            metrics,
            available_fields=available_fields,
        ),
        "channels": build_channel_analysis(
            data_frame,
            available_fields=available_fields,
        ),
    }


def build_analysis_metadata(
    data_frame: pd.DataFrame,
    file_name: str,
    *,
    available_fields: frozenset[str] | None = None,
) -> dict[str, Any]:
    resolved_fields = available_fields or frozenset(data_frame.columns)
    available_time_columns = [
        column for column in TIME_COLUMNS if column in resolved_fields
    ]
    timestamp_values = pd.concat(
        [data_frame[column].dropna() for column in available_time_columns],
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


def calculate_metrics(
    data_frame: pd.DataFrame,
    *,
    available_fields: frozenset[str] | None = None,
) -> dict[str, Any]:
    resolved_fields = available_fields or frozenset(data_frame.columns)
    stage_masks = _build_stage_masks(data_frame, resolved_fields)
    user_counts: dict[str, int | None] = {}
    for stage_key, _, timestamp_column in FUNNEL_STAGES:
        if _stage_is_available(
            stage_key,
            timestamp_column,
            resolved_fields,
        ):
            user_counts[stage_key] = int(stage_masks[stage_key].sum())
        else:
            user_counts[stage_key] = None
    conversion_rates = _build_conversion_rates(
        user_counts,
        resolved_fields,
    )

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


def build_funnel(
    metrics: dict[str, Any],
    *,
    available_fields: frozenset[str] | None = None,
) -> dict[str, Any]:
    counts = metrics["user_counts"]
    stages: list[dict[str, Any]] = []
    previous_count: int | None = None
    resolved_fields = available_fields or frozenset(TIME_COLUMNS)

    for stage_key, label, timestamp_column in FUNNEL_STAGES:
        if not _stage_is_available(stage_key, timestamp_column, resolved_fields):
            continue
        current_count = counts[stage_key]
        if current_count is None:
            continue
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


def build_channel_analysis(
    data_frame: pd.DataFrame,
    *,
    available_fields: frozenset[str] | None = None,
) -> dict[str, Any]:
    resolved_fields = available_fields or frozenset(data_frame.columns)
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
            data_frame.loc[data_frame["channel"] == channel].copy(),
            available_fields=resolved_fields,
        )
        for channel in ordered_channels
    }


def _build_stage_masks(
    data_frame: pd.DataFrame,
    available_fields: frozenset[str],
) -> dict[str, pd.Series]:
    masks: dict[str, pd.Series] = {}
    previous_mask = pd.Series(True, index=data_frame.index, dtype=bool)

    for stage_key, _, timestamp_column in FUNNEL_STAGES:
        if stage_key == "paid_users" and "pay_time" not in available_fields:
            current_mask = previous_mask & data_frame["order_amount"].gt(0)
        elif timestamp_column in available_fields:
            current_mask = previous_mask & data_frame[timestamp_column].notna()
        else:
            masks[stage_key] = pd.Series(
                False,
                index=data_frame.index,
                dtype=bool,
            )
            continue
        masks[stage_key] = current_mask
        previous_mask = current_mask

    return masks


def _build_conversion_rates(
    user_counts: dict[str, int | None],
    available_fields: frozenset[str],
) -> dict[str, float | None]:
    rate_keys = {
        "viewed_users": "view_rate",
        "lead_users": "lead_rate",
        "appointment_users": "appointment_rate",
        "visit_users": "visit_rate",
        "paid_users": "paid_rate",
    }
    conversion_rates: dict[str, float | None] = {
        rate_key: None for rate_key in rate_keys.values()
    }
    previous_stage_key = "registered_users"

    for stage_key, _, timestamp_column in FUNNEL_STAGES[1:]:
        if not _stage_is_available(
            stage_key,
            timestamp_column,
            available_fields,
        ):
            continue
        current_count = user_counts[stage_key]
        previous_count = user_counts[previous_stage_key]
        if current_count is None or previous_count is None:
            continue
        conversion_rates[rate_keys[stage_key]] = _safe_rate(
            current_count,
            previous_count,
        )
        previous_stage_key = stage_key

    return conversion_rates


def _stage_is_available(
    stage_key: str,
    timestamp_column: str,
    available_fields: frozenset[str],
) -> bool:
    if stage_key == "registered_users":
        return "register_time" in available_fields
    if stage_key == "paid_users":
        return (
            "pay_time" in available_fields
            or "order_amount" in available_fields
        )
    return timestamp_column in available_fields


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)
