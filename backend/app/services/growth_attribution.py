from collections.abc import Iterable

from app.schemas.aggregate_analysis import (
    DimensionFunnelDiagnosis,
    DimensionPerformance,
)
from app.schemas.growth_attribution import (
    DimensionGrowthAttribution,
    FunnelContributionAnalysis,
    TrafficChange,
    UserScaleAnalysis,
    ConversionChange,
)


SCALE_STABLE_THRESHOLD = 0.02
RATE_PP_STABLE_THRESHOLD = 0.005
RATE_RATIO_STABLE_THRESHOLD = 0.02


def build_growth_attribution(
    dimension_performance: Iterable[DimensionPerformance],
    dimension_diagnosis: Iterable[DimensionFunnelDiagnosis],
) -> list[DimensionGrowthAttribution]:
    """Explain growth direction from validated scale and funnel movements.

    The attribution is deterministic and descriptive. It does not claim causal
    lift: when a driver is selected, the explanation explicitly describes the
    observed combination of traffic, payment and conversion movements.
    """

    diagnosis_lookup = {
        item.dimension_value: item for item in dimension_diagnosis
    }
    return [
        _attribute_dimension(item, diagnosis_lookup.get(item.dimension_value))
        for item in dimension_performance
    ]


def _attribute_dimension(
    performance: DimensionPerformance,
    diagnosis: DimensionFunnelDiagnosis | None,
) -> DimensionGrowthAttribution:
    changes = {item.metric_key: item for item in performance.scale_changes}
    traffic_yoy = _ratio_change(changes.get("traffic_users"), "yoy")
    booking_yoy = _ratio_change(changes.get("appointment_users"), "yoy")
    payment_yoy = _ratio_change(changes.get("payment_users"), "yoy")
    conversion_yoy = diagnosis.final_conversion_yoy if diagnosis else None
    conversion_unit = (
        diagnosis.final_conversion_yoy_unit if diagnosis else None
    )

    traffic_trend = _trend(traffic_yoy, SCALE_STABLE_THRESHOLD)
    booking_trend = _trend(booking_yoy, SCALE_STABLE_THRESHOLD)
    payment_trend = _trend(payment_yoy, SCALE_STABLE_THRESHOLD)
    conversion_trend = _conversion_trend(conversion_yoy, conversion_unit)
    driver = _resolve_driver(
        traffic_trend=traffic_trend,
        payment_trend=payment_trend,
        conversion_trend=conversion_trend,
        traffic_yoy=traffic_yoy,
        payment_yoy=payment_yoy,
    )
    limitations: list[str] = []
    if traffic_yoy is None:
        limitations.append("缺少浏览用户同比数据。")
    if payment_yoy is None:
        limitations.append("缺少支付用户同比数据。")
    if conversion_yoy is None:
        limitations.append("缺少支付转化率同比数据。")

    return DimensionGrowthAttribution(
        dimension_value=performance.dimension_value,
        traffic_change=TrafficChange(
            browse_users_yoy=traffic_yoy,
            booking_users_yoy=booking_yoy,
            payment_users_yoy=payment_yoy,
            unit=(
                "ratio_change"
                if any(
                    value is not None
                    for value in (traffic_yoy, booking_yoy, payment_yoy)
                )
                else None
            ),
        ),
        conversion_change=ConversionChange(
            payment_rate_change=conversion_yoy,
            unit=conversion_unit,
        ),
        user_scale_analysis=UserScaleAnalysis(
            traffic_trend=traffic_trend,
            booking_user_trend=booking_trend,
            payment_user_trend=payment_trend,
            scale_contribution=_scale_contribution(payment_trend),
        ),
        funnel_contribution_analysis=_funnel_contribution(diagnosis),
        growth_driver=driver,
        driver_explanation=_driver_explanation(
            driver,
            traffic_trend,
            payment_trend,
            conversion_trend,
        ),
        limitations=limitations,
    )


def _ratio_change(change, period: str) -> float | None:
    if change is None:
        return None
    value = getattr(change, f"{period}_change")
    unit = getattr(change, f"{period}_unit")
    if value is None:
        return None
    if unit == "ratio_change":
        return value
    if unit != "absolute_change" or change.current_value is None:
        return None
    baseline = change.current_value - value
    if baseline <= 0:
        return None
    return round(value / baseline, 6)


def _trend(value: float | None, threshold: float) -> str:
    if value is None:
        return "unavailable"
    if value > threshold:
        return "growth"
    if value < -threshold:
        return "decline"
    return "stable"


def _conversion_trend(value: float | None, unit: str | None) -> str:
    threshold = (
        RATE_PP_STABLE_THRESHOLD
        if unit == "percentage_point"
        else RATE_RATIO_STABLE_THRESHOLD
    )
    return _trend(value, threshold)


def _resolve_driver(
    *,
    traffic_trend: str,
    payment_trend: str,
    conversion_trend: str,
    traffic_yoy: float | None,
    payment_yoy: float | None,
) -> str:
    if traffic_yoy is None or payment_yoy is None:
        return "unavailable"
    if traffic_trend == "growth" and conversion_trend == "growth":
        return "combined"
    if conversion_trend == "growth":
        return "conversion"
    if traffic_trend == "growth":
        return "traffic"
    if (
        traffic_yoy is not None
        and payment_yoy is not None
        and payment_yoy > traffic_yoy + SCALE_STABLE_THRESHOLD
    ):
        return "conversion"
    if payment_trend == "unavailable":
        return "unavailable"
    return "mixed"


def _scale_contribution(payment_trend: str) -> str:
    return {
        "growth": "positive",
        "decline": "negative",
        "stable": "neutral",
        "unavailable": "unavailable",
    }[payment_trend]


def _driver_explanation(
    driver: str,
    traffic_trend: str,
    payment_trend: str,
    conversion_trend: str,
) -> str:
    if driver == "combined":
        return "支付增长同时伴随流量扩大和转化效率改善，呈现双重驱动。"
    if driver == "traffic":
        if conversion_trend == "decline":
            return "支付表现主要由流量扩大支撑，但转化效率承压。"
        return "支付表现主要伴随流量规模扩大，转化效率变化有限。"
    if driver == "conversion":
        if payment_trend == "decline":
            return "转化效率有所改善，但规模下降抵消了效率贡献。"
        if traffic_trend == "decline":
            return "支付表现主要受转化效率改善支撑，流量下降形成抵消。"
        return "支付表现主要伴随转化效率改善，而非流量明显扩大。"
    if driver == "mixed":
        return "流量、支付规模与转化效率方向不一致，暂不能归为单一驱动。"
    return "同比规模或转化数据不足，暂无法可靠判断增长来源。"


def _funnel_contribution(
    diagnosis: DimensionFunnelDiagnosis | None,
) -> FunnelContributionAnalysis:
    if diagnosis is None:
        return FunnelContributionAnalysis(
            primary_contribution_stage=None,
            primary_drag_stage=None,
            weakest_stage=None,
        )
    return FunnelContributionAnalysis(
        primary_contribution_stage=_movement_label(
            diagnosis.best_improving_stage
        ),
        primary_drag_stage=_movement_label(
            diagnosis.largest_declining_stage
        ),
        weakest_stage=(
            f"{diagnosis.weakest_stage.from_label}→"
            f"{diagnosis.weakest_stage.to_label}"
            if diagnosis.weakest_stage
            else None
        ),
    )


def _movement_label(movement) -> str | None:
    if movement is None:
        return None
    return f"{movement.from_label}→{movement.to_label}"
