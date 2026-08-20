from app.schemas.aggregate_analysis import (
    DimensionFunnelDiagnosis,
    DimensionFunnelStage,
    DimensionPerformance,
)
from app.schemas.growth_attribution import ScaleMetricChange
from app.services.cross_metric_diagnosis import (
    build_cross_metric_diagnoses,
    build_cross_metric_summary,
)
from app.services.growth_attribution import build_growth_attribution


def _performance(
    dimension_value: str,
    *,
    traffic_users: int = 10_000,
    appointment_users: int = 3_000,
    payment_users: int = 1_000,
    conversion_rate: float = 0.1,
    traffic_yoy: float | None = 0.0,
    booking_yoy: float | None = 0.0,
    payment_yoy: float | None = 0.0,
) -> DimensionPerformance:
    changes = []
    for metric_key, label, current_value, yoy_change in (
        ("traffic_users", "浏览用户", traffic_users, traffic_yoy),
        ("appointment_users", "预约用户", appointment_users, booking_yoy),
        ("payment_users", "支付用户", payment_users, payment_yoy),
    ):
        changes.append(
            ScaleMetricChange(
                metric_key=metric_key,
                label=label,
                current_value=current_value,
                yoy_change=yoy_change,
                yoy_unit="ratio_change" if yoy_change is not None else None,
                mom_change=None,
                mom_unit=None,
            )
        )
    return DimensionPerformance(
        dimension_value=dimension_value,
        traffic_users=traffic_users,
        appointment_users=appointment_users,
        payment_users=payment_users,
        conversion_rate=conversion_rate,
        gmv=None,
        average_order_value=None,
        yoy=None,
        mom=None,
        yoy_unit=None,
        mom_unit=None,
        scale_changes=changes,
        supplemental_outcomes=[],
    )


def _diagnosis(
    dimension_value: str,
    *,
    final_conversion_rate: float = 0.1,
    conversion_yoy: float | None = 0.0,
    conversion_mom: float | None = None,
    stage_yoy: float | None = None,
    stage_mom: float | None = None,
    stage_rate: float = 0.4,
) -> DimensionFunnelDiagnosis:
    stage = DimensionFunnelStage(
        from_metric_key="product_detail_users",
        from_label="商详",
        to_metric_key="appointment_users",
        to_label="预约",
        current_conversion_rate=stage_rate,
        yoy_delta=stage_yoy,
        mom_delta=stage_mom,
        yoy_unit="percentage_point" if stage_yoy is not None else None,
        mom_unit="percentage_point" if stage_mom is not None else None,
    )
    return DimensionFunnelDiagnosis(
        dimension_value=dimension_value,
        final_conversion_rate=final_conversion_rate,
        final_conversion_yoy=conversion_yoy,
        final_conversion_mom=conversion_mom,
        final_conversion_yoy_unit=(
            "percentage_point" if conversion_yoy is not None else None
        ),
        final_conversion_mom_unit=(
            "percentage_point" if conversion_mom is not None else None
        ),
        stages=[stage],
        best_improving_stage=None,
        largest_declining_stage=None,
        weakest_stage=None,
        diagnosis_level="attention",
    )


def _build(
    performances: list[DimensionPerformance],
    diagnoses: list[DimensionFunnelDiagnosis],
):
    attributions = build_growth_attribution(performances, diagnoses)
    return build_cross_metric_diagnoses(
        performances,
        diagnoses,
        attributions,
    )


def test_traffic_down_conversion_up_and_payment_down_are_joined() -> None:
    results = _build(
        [
            _performance(
                "品类甲",
                traffic_yoy=-0.1,
                payment_yoy=-0.05,
                conversion_rate=0.15,
            )
        ],
        [_diagnosis("品类甲", final_conversion_rate=0.15, conversion_yoy=0.04)],
    )

    result = results[0]
    assert "traffic_down_conversion_up" in result.diagnosis_patterns
    assert "conversion_up_payment_down" in result.diagnosis_patterns
    assert result.outcome_state.startswith("支付用户下降")
    assert result.attribution_driver == "conversion"


def test_traffic_up_conversion_down_and_payment_flat_are_joined() -> None:
    result = _build(
        [_performance("品类甲", traffic_yoy=0.2, payment_yoy=0.0)],
        [_diagnosis("品类甲", conversion_yoy=-0.03)],
    )[0]

    assert "traffic_up_conversion_down" in result.diagnosis_patterns
    assert "traffic_up_payment_flat" in result.diagnosis_patterns
    assert "cross_metric_contradiction" in result.diagnosis_patterns


def test_positive_scale_and_conversion_growth_is_not_high_priority_risk() -> None:
    result = _build(
        [_performance("品类甲", traffic_yoy=0.12, payment_yoy=0.18)],
        [_diagnosis("品类甲", conversion_yoy=0.03, stage_yoy=0.02)],
    )[0]

    assert "traffic_up_conversion_up" in result.diagnosis_patterns
    assert result.priority_level == "low"
    assert result.priority_score <= 30


def test_final_conversion_improvement_and_front_funnel_loss_is_contradiction() -> None:
    result = _build(
        [_performance("品类甲", traffic_yoy=0.0, payment_yoy=0.05)],
        [_diagnosis("品类甲", conversion_yoy=0.04, stage_yoy=-0.0742)],
    )[0]

    assert "cross_metric_contradiction" in result.diagnosis_patterns
    assert "funnel_front_loss" in result.diagnosis_patterns
    assert result.primary_bottleneck is not None
    assert result.primary_bottleneck.stage == "商详→预约"


def test_yoy_improvement_and_mom_decline_is_reversal_signal() -> None:
    result = _build(
        [_performance("品类甲", traffic_yoy=0.0, payment_yoy=0.05)],
        [_diagnosis("品类甲", conversion_yoy=0.04, conversion_mom=-0.02)],
    )[0]

    assert "yoy_up_mom_down" in result.diagnosis_patterns
    assert result.secondary_signal is not None
    assert result.secondary_signal.signal_type == "yoy_up_mom_down"


def test_large_dimension_with_same_funnel_loss_has_higher_priority() -> None:
    performances = [
        _performance("大品类", traffic_users=100_000, payment_users=8_000),
        _performance("小品类", traffic_users=2_000, payment_users=160),
        _performance("对照甲", traffic_users=15_000, payment_users=3_000),
        _performance("对照乙", traffic_users=12_000, payment_users=2_400),
    ]
    diagnoses = [
        _diagnosis("大品类", stage_rate=0.3, stage_yoy=-0.04),
        _diagnosis("小品类", stage_rate=0.3, stage_yoy=-0.04),
        _diagnosis("对照甲", stage_rate=0.8),
        _diagnosis("对照乙", stage_rate=0.8),
    ]
    results = {item.dimension_value: item for item in _build(performances, diagnoses)}

    assert results["大品类"].priority_score > results["小品类"].priority_score
    assert results["大品类"].primary_bottleneck is not None
    assert results["小品类"].primary_bottleneck is not None
    assert results["大品类"].conversion.peer_median_value == 0.1
    assert results["大品类"].conversion.rank is not None


def test_missing_traffic_yoy_degrades_without_inventing_driver_pattern() -> None:
    result = _build(
        [_performance("品类甲", traffic_yoy=None, payment_yoy=0.05)],
        [_diagnosis("品类甲", conversion_yoy=0.03)],
    )[0]

    assert not any(pattern.startswith("traffic_") for pattern in result.diagnosis_patterns)
    assert result.attribution_driver == "unavailable"
    assert "缺少浏览用户同比，流量方向不参与确定性模式判断。" in result.limitations


def test_summary_marks_dimension_only_when_no_safe_overall_scope() -> None:
    diagnoses = _build(
        [_performance("品类甲", traffic_yoy=-0.1, payment_yoy=-0.05)],
        [_diagnosis("品类甲", conversion_yoy=0.04)],
    )

    summary = build_cross_metric_summary(
        diagnoses,
        has_safe_overall_scope=False,
    )

    assert summary.scope == "dimension_only"
    assert summary.top_priority_dimensions == ["品类甲"]


def test_scale_trend_reuses_growth_attribution_for_absolute_changes() -> None:
    performance = _performance("品类甲", traffic_yoy=None, payment_yoy=None)
    changes = list(performance.scale_changes)
    changes[0] = changes[0].model_copy(
        update={"yoy_change": 1, "yoy_unit": "absolute_change"}
    )
    changes[2] = changes[2].model_copy(
        update={"yoy_change": 1, "yoy_unit": "absolute_change"}
    )
    performance = performance.model_copy(update={"scale_changes": changes})

    result = _build(
        [performance],
        [_diagnosis("品类甲", conversion_yoy=-0.03)],
    )[0]

    assert result.traffic.trend == "stable"
    assert result.payment.trend == "stable"
    assert "traffic_up_conversion_down" not in result.diagnosis_patterns
