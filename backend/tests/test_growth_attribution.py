from app.schemas.aggregate_analysis import (
    DimensionFunnelDiagnosis,
    DimensionPerformance,
)
from app.services.growth_attribution import build_growth_attribution


def test_traffic_growth_with_conversion_decline_is_traffic_driven() -> None:
    result = _attribute(
        traffic_yoy=0.20,
        payment_yoy=0.10,
        conversion_yoy=-0.04,
    )

    assert result.growth_driver == "traffic"
    assert result.user_scale_analysis.traffic_trend == "growth"
    assert "转化效率承压" in result.driver_explanation


def test_conversion_improves_while_payment_users_decline() -> None:
    result = _attribute(
        traffic_yoy=-0.12,
        payment_yoy=-0.05,
        conversion_yoy=0.04,
    )

    assert result.growth_driver == "conversion"
    assert result.user_scale_analysis.payment_user_trend == "decline"
    assert result.user_scale_analysis.scale_contribution == "negative"
    assert "规模下降抵消" in result.driver_explanation


def test_traffic_and_conversion_growth_are_combined_driver() -> None:
    result = _attribute(
        traffic_yoy=0.10,
        payment_yoy=0.25,
        conversion_yoy=0.04,
    )

    assert result.growth_driver == "combined"
    assert result.user_scale_analysis.scale_contribution == "positive"


def test_missing_yoy_data_degrades_without_guessing() -> None:
    result = _attribute(
        traffic_yoy=None,
        payment_yoy=None,
        conversion_yoy=None,
    )

    assert result.growth_driver == "unavailable"
    assert result.user_scale_analysis.traffic_trend == "unavailable"
    assert len(result.limitations) == 3


def test_conversion_change_alone_cannot_explain_payment_growth() -> None:
    result = _attribute(
        traffic_yoy=None,
        payment_yoy=None,
        conversion_yoy=0.04,
    )

    assert result.growth_driver == "unavailable"
    assert "暂无法可靠判断" in result.driver_explanation


def _attribute(
    *,
    traffic_yoy: float | None,
    payment_yoy: float | None,
    conversion_yoy: float | None,
):
    scale_changes = [
        {
            "metric_key": "traffic_users",
            "label": "浏览用户",
            "current_value": 1000,
            "yoy_change": traffic_yoy,
            "yoy_unit": "ratio_change" if traffic_yoy is not None else None,
            "mom_change": None,
            "mom_unit": None,
        },
        {
            "metric_key": "appointment_users",
            "label": "预约用户",
            "current_value": 300,
            "yoy_change": None,
            "yoy_unit": None,
            "mom_change": None,
            "mom_unit": None,
        },
        {
            "metric_key": "payment_users",
            "label": "支付用户",
            "current_value": 150,
            "yoy_change": payment_yoy,
            "yoy_unit": "ratio_change" if payment_yoy is not None else None,
            "mom_change": None,
            "mom_unit": None,
        },
    ]
    performance = DimensionPerformance(
        dimension_value="品类甲",
        traffic_users=1000,
        appointment_users=300,
        payment_users=150,
        conversion_rate=0.15,
        gmv=None,
        average_order_value=None,
        yoy=conversion_yoy,
        mom=None,
        yoy_unit=(
            "percentage_point" if conversion_yoy is not None else None
        ),
        mom_unit=None,
        scale_changes=scale_changes,
        supplemental_outcomes=[],
    )
    diagnosis = DimensionFunnelDiagnosis(
        dimension_value="品类甲",
        final_conversion_rate=0.15,
        final_conversion_yoy=conversion_yoy,
        final_conversion_mom=None,
        final_conversion_yoy_unit=(
            "percentage_point" if conversion_yoy is not None else None
        ),
        final_conversion_mom_unit=None,
        stages=[],
        best_improving_stage=None,
        largest_declining_stage=None,
        weakest_stage=None,
        diagnosis_level="stable",
    )
    return build_growth_attribution([performance], [diagnosis])[0]
