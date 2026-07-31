from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from app.services.excel_parser import REQUIRED_COLUMNS


TIME_COLUMNS = (
    "register_time",
    "view_time",
    "lead_time",
    "appointment_time",
    "visit_time",
    "pay_time",
)
CORE_CHANNELS = ("小红书", "抖音", "微信", "自然流量")
UNKNOWN_CHANNEL = "未知"


@dataclass(frozen=True)
class CleaningResult:
    data_frame: pd.DataFrame
    data_quality_summary: dict[str, Any]


def clean_growth_data(data_frame: pd.DataFrame) -> CleaningResult:
    """Normalize uploaded user-level data and return inspectable quality evidence."""
    working = data_frame.loc[:, list(REQUIRED_COLUMNS)].copy()
    working["_source_row"] = range(len(working))
    original_user_count = len(working)

    issue_rows: set[int] = set()
    issue_counts = {
        "missing_user_id": 0,
        "duplicate_user_id": 0,
        "unknown_channel": 0,
        "invalid_time": 0,
        "future_time": 0,
        "invalid_event_order": 0,
        "invalid_amount": 0,
        "negative_amount": 0,
        "amount_without_payment": 0,
    }

    working["user_id"] = working["user_id"].map(_normalize_user_id)
    missing_user_mask = working["user_id"].isna()
    issue_counts["missing_user_id"] = int(missing_user_mask.sum())
    issue_rows.update(working.loc[missing_user_mask, "_source_row"].astype(int))
    working = working.loc[~missing_user_mask].copy()

    working["_completeness_score"] = working.loc[:, list(REQUIRED_COLUMNS)].apply(
        lambda row: sum(_has_value(value) for value in row),
        axis=1,
    )
    preferred_rows = working.sort_values(
        by=["user_id", "_completeness_score", "_source_row"],
        ascending=[True, False, True],
        kind="stable",
    )
    duplicate_mask = preferred_rows.duplicated(subset="user_id", keep="first")
    duplicate_sources = preferred_rows.loc[duplicate_mask, "_source_row"].astype(int)
    issue_counts["duplicate_user_id"] = int(duplicate_mask.sum())
    issue_rows.update(duplicate_sources)
    working = (
        preferred_rows.loc[~duplicate_mask]
        .sort_values("_source_row", kind="stable")
        .drop(columns="_completeness_score")
        .reset_index(drop=True)
    )

    original_channel = working["channel"]
    empty_channel_mask = ~original_channel.map(_has_value)
    issue_counts["unknown_channel"] = int(empty_channel_mask.sum())
    issue_rows.update(
        working.loc[empty_channel_mask, "_source_row"].astype(int)
    )
    working["channel"] = original_channel.map(_normalize_channel)

    future_cutoff = pd.Timestamp(datetime.now() + timedelta(days=1))
    for column in TIME_COLUMNS:
        raw_values = working[column]
        present_mask = raw_values.map(_has_value)
        parsed_values = pd.to_datetime(
            raw_values,
            errors="coerce",
            format="mixed",
            utc=True,
        )
        parsed_values = parsed_values.dt.tz_localize(None)

        invalid_mask = present_mask & parsed_values.isna()
        issue_counts["invalid_time"] += int(invalid_mask.sum())
        issue_rows.update(
            working.loc[invalid_mask, "_source_row"].astype(int)
        )

        future_mask = parsed_values.notna() & (parsed_values > future_cutoff)
        issue_counts["future_time"] += int(future_mask.sum())
        issue_rows.update(
            working.loc[future_mask, "_source_row"].astype(int)
        )
        parsed_values = parsed_values.mask(future_mask, pd.NaT)
        working[column] = parsed_values

    invalid_order_rows: set[int] = set()
    for row_index, row in working.iterrows():
        previous_time: pd.Timestamp | None = None
        path_is_complete = True

        for column in TIME_COLUMNS:
            current_time = row[column]
            if pd.isna(current_time):
                path_is_complete = False
                continue

            if not path_is_complete or (
                previous_time is not None and current_time < previous_time
            ):
                working.at[row_index, column] = pd.NaT
                invalid_order_rows.add(int(row["_source_row"]))
                path_is_complete = False
                continue

            previous_time = current_time

    issue_counts["invalid_event_order"] = len(invalid_order_rows)
    issue_rows.update(invalid_order_rows)

    raw_amount = working["order_amount"]
    amount_present_mask = raw_amount.map(_has_value)
    numeric_amount = pd.to_numeric(raw_amount, errors="coerce")
    invalid_amount_mask = amount_present_mask & numeric_amount.isna()
    negative_amount_mask = numeric_amount.notna() & (numeric_amount < 0)

    issue_counts["invalid_amount"] = int(invalid_amount_mask.sum())
    issue_counts["negative_amount"] = int(negative_amount_mask.sum())
    issue_rows.update(
        working.loc[
            invalid_amount_mask | negative_amount_mask,
            "_source_row",
        ].astype(int)
    )

    numeric_amount = numeric_amount.fillna(0).clip(lower=0)
    amount_without_payment_mask = (
        numeric_amount.gt(0) & working["pay_time"].isna()
    )
    issue_counts["amount_without_payment"] = int(
        amount_without_payment_mask.sum()
    )
    issue_rows.update(
        working.loc[
            amount_without_payment_mask,
            "_source_row",
        ].astype(int)
    )
    numeric_amount.loc[amount_without_payment_mask] = 0
    working["order_amount"] = numeric_amount.astype(float)

    valid_user_count = len(working)
    removed_count = original_user_count - valid_user_count
    data_completeness = _calculate_data_completeness(working)

    cleaned_frame = working.drop(columns="_source_row").reset_index(drop=True)
    return CleaningResult(
        data_frame=cleaned_frame,
        data_quality_summary={
            "original_user_count": original_user_count,
            "valid_user_count": valid_user_count,
            "removed_count": removed_count,
            "anomaly_count": len(issue_rows),
            "data_completeness": data_completeness,
            "issue_counts": issue_counts,
        },
    )


def _calculate_data_completeness(data_frame: pd.DataFrame) -> float:
    """Measure required-field coverage without penalizing normal funnel drop-off."""
    if data_frame.empty:
        return 0.0

    required_slots = len(data_frame) * 3
    complete_slots = (
        data_frame["user_id"].notna().sum()
        + data_frame["channel"].ne(UNKNOWN_CHANNEL).sum()
        + data_frame["register_time"].notna().sum()
    )

    paid_mask = data_frame["pay_time"].notna()
    required_slots += int(paid_mask.sum())
    complete_slots += int(
        (paid_mask & data_frame["order_amount"].gt(0)).sum()
    )
    return round(float(complete_slots / required_slots), 4)


def _normalize_user_id(value: Any) -> str | None:
    if not _has_value(value):
        return None
    normalized = str(value).strip()
    if normalized.endswith(".0") and normalized[:-2].isdigit():
        return normalized[:-2]
    return normalized


def _normalize_channel(value: Any) -> str:
    if not _has_value(value):
        return UNKNOWN_CHANNEL
    normalized = str(value).strip()
    return normalized or UNKNOWN_CHANNEL


def _has_value(value: Any) -> bool:
    if value is None or pd.isna(value):
        return False
    return bool(str(value).strip())
